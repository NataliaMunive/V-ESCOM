"""
Router de Gestión de Streams RTSP - V-ESCOM (CU06)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import cv2
import os
import logging
import socket
import time
from urllib.parse import urlsplit

from app.bd import get_db
from app.core.deps import get_current_admin
from app.core.security import decode_access_token
from app.models.administrador import Administrador
from app.models.camara import Camara
from app.services.rtsp_manager import rtsp_manager, resolver_rtsp_url_camara
from pydantic import BaseModel

log = logging.getLogger("rtsp_routes")
router = APIRouter(prefix="/rtsp", tags=["RTSP / Captura Continua"])


def _prevalidar_rtsp(rtsp_url: str, timeout_ms: int = 6000) -> tuple[bool, str]:
    """
    Verifica rápidamente si la URL RTSP puede abrirse antes de iniciar el worker.
    Evita esperar los reintentos largos del ciclo principal para errores de credenciales/URL.
    """
    os.environ.setdefault(
        "OPENCV_FFMPEG_CAPTURE_OPTIONS",
        "rtsp_transport;tcp|stimeout;6000000|max_delay;5000000|fflags;nobuffer",
    )

    # Validación rápida de conectividad al host/puerto antes de abrir con OpenCV.
    # Si falla aquí, el problema suele ser red, cámara apagada o URL/host incorrecto.
    try:
        partes = urlsplit(rtsp_url)
        host = partes.hostname
        puerto = partes.port or 554
        if host:
            with socket.create_connection((host, puerto), timeout=3):
                pass
    except Exception:
        return False, f"No hay conexión al host RTSP {rtsp_url}"

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)  # type: ignore
    try:
        # Algunos backends de OpenCV soportan estos timeouts; si no, simplemente se ignoran.
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)  # type: ignore
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)  # type: ignore
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # type: ignore

        if not cap.isOpened():
            return False, "No se pudo abrir el stream RTSP."

        # Intentar leer un frame confirma autenticación + path de stream + decodificación básica.
        ret, _frame = cap.read()
        if not ret:
            return False, "La conexión abrió pero no entregó frames."

        return True, "ok"
    finally:
        cap.release()


MJPEG_PUSH_FPS = float(os.getenv("MJPEG_PUSH_FPS", "15"))


def _marcar_camara_activa(db: Session, id_camara: int) -> None:
    camara = db.query(Camara).filter(Camara.id_camara == id_camara).first()
    if camara is not None:
        camara.activa = True
        camara.estado = "Activa"
        db.commit()


class IniciarStreamPayload(BaseModel):
    id_camara: int
    rtsp_url: Optional[str] = None
    rtsp_user: Optional[str] = "adminadmin"
    rtsp_pass: Optional[str] = ""
    stream: Optional[str] = "stream2"


@router.post("/iniciar")
async def iniciar_stream(
    payload: IniciarStreamPayload,
    db: Session = Depends(get_db),
    admin: Administrador = Depends(get_current_admin),
):
    rtsp_url = payload.rtsp_url
    if not rtsp_url:
        camara = db.query(Camara).filter(Camara.id_camara == payload.id_camara).first()
        if not camara:
            raise HTTPException(status_code=404, detail="Cámara no encontrada")
        if not camara.direccion_ip:
            raise HTTPException(status_code=422, detail="La cámara no tiene IP o URL configurada.")
        rtsp_url = resolver_rtsp_url_camara(
            camara,
            payload.id_camara,
            user=payload.rtsp_user,
            pwd=payload.rtsp_pass,
            stream=payload.stream,
        )
    log.info(f"URL RTSP que se usará: {rtsp_url}")

    ok, detalle = await run_in_threadpool(_prevalidar_rtsp, rtsp_url)
    if not ok:
        raise HTTPException(
            status_code=422,
            detail=(
                "Falló la validación previa del stream. "
                f"Detalle: {detalle} "
                "Verifica usuario/contraseña (incluyendo mayúsculas), "
                "URL codificada (%21 para '!') y stream (stream1/stream2)."
            ),
        )

    from app.core.security import create_access_token
    token = create_access_token({"sub": str(admin.id_admin), "email": admin.email})
    rtsp_manager.set_token(token)
    await rtsp_manager.iniciar_camara(payload.id_camara, rtsp_url)
    _marcar_camara_activa(db, payload.id_camara)
    return {"mensaje": f"Worker iniciado para cámara #{payload.id_camara}", "rtsp_url": rtsp_url}


@router.delete("/detener/{id_camara}")
def detener_stream(id_camara: int, _admin: Administrador = Depends(get_current_admin)):
    rtsp_manager.detener_camara(id_camara)
    return {"mensaje": f"Worker detenido para cámara #{id_camara}"}


@router.get("/estado")
def estado_streams(_admin: Administrador = Depends(get_current_admin)):
    return rtsp_manager.estado()


@router.get("/snapshot/{id_camara}")
async def snapshot(
    id_camara: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    # Intentar servir desde ultimo_jpg del worker primero
    worker = rtsp_manager._workers.get(id_camara)
    if worker and worker.activo and worker.ultimo_jpg:
        return Response(content=worker.ultimo_jpg, media_type="image/jpeg")

    # Fallback: capturar directamente
    worker = rtsp_manager._workers.get(id_camara)
    if worker and worker.activo:
        rtsp_url = worker.rtsp_url
    else:
        camara = db.query(Camara).filter(Camara.id_camara == id_camara).first()
        if not camara:
            raise HTTPException(status_code=404, detail="Cámara no encontrada")
        if not camara.direccion_ip:
            raise HTTPException(status_code=422, detail="La cámara no tiene IP o URL configurada.")
        rtsp_url = resolver_rtsp_url_camara(camara, id_camara)

    def _capturar() -> bytes:
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)  # type: ignore
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # type: ignore
        if not cap.isOpened():
            return b""
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return b""
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])  # type: ignore
        return buf.tobytes() if ok else b""

    jpg = await asyncio.get_event_loop().run_in_executor(None, _capturar)
    if not jpg:
        raise HTTPException(status_code=503, detail="No se pudo capturar frame.")
    return Response(content=jpg, media_type="image/jpeg")


@router.get("/mjpeg/{id_camara}")
async def mjpeg_stream(
    id_camara: int,
    token: str = Query(..., description="JWT del administrador"),
    db: Session = Depends(get_db),
):
    """
    Stream MJPEG — lee frames de worker.ultimo_jpg sin abrir conexión RTSP extra.
    Autenticación via ?token=... porque los <img> no envían headers.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    admin = db.query(Administrador).filter(
        Administrador.id_admin == int(admin_id),
        Administrador.activo.is_(True)
    ).first()
    if not admin:
        raise HTTPException(status_code=401, detail="No autorizado")

    # Autorrecuperación: si no existe worker activo, re-iniciarlo automáticamente.
    worker = rtsp_manager._workers.get(id_camara)
    if not worker or not worker.activo:
        camara = db.query(Camara).filter(Camara.id_camara == id_camara).first()
        if not camara:
            raise HTTPException(status_code=404, detail="Cámara no encontrada")
        if not camara.direccion_ip:
            raise HTTPException(status_code=422, detail="La cámara no tiene IP o URL configurada.")

        try:
            rtsp_url = resolver_rtsp_url_camara(camara, id_camara)
            rtsp_manager.set_token(token)
            await rtsp_manager.iniciar_camara(id_camara, rtsp_url)
            _marcar_camara_activa(db, id_camara)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"No se pudo iniciar el stream automáticamente: {e}",
            )

        worker = rtsp_manager._workers.get(id_camara)
        if not worker or not worker.activo:
            raise HTTPException(status_code=503, detail="Stream no activo.")

    log.info(f"[MJPEG Cam#{id_camara}] Cliente conectado")

    async def generar_frames():
        """
        Lee ultimo_jpg del worker directamente.
        NO abre conexión RTSP — evita conflicto con el worker de captura.
        """
        try:
            max_stale_seg = 4.0
            sleep_seg = 1.0 / max(MJPEG_PUSH_FPS, 1.0)
            while worker.activo:
                jpg = worker.ultimo_jpg

                if jpg is None:
                    await asyncio.sleep(sleep_seg)
                    continue

                # Si no hay frame nuevo en varios segundos, cerramos este stream
                # para forzar reconexión del cliente y evitar imagen congelada.
                age = time.time() - (worker.ultimo_jpg_ts or 0.0)
                if age > max_stale_seg:
                    log.warning(
                        f"[MJPEG Cam#{id_camara}] Frame estancado por {age:.1f}s; cerrando conexión."
                    )
                    await asyncio.sleep(sleep_seg)
                    break

                # Reenviar el último frame disponible mantiene la conexión viva
                # y evita flashes negros cuando el stream se queda sin un frame nuevo.
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpg
                    + b"\r\n"
                )

                await asyncio.sleep(sleep_seg)

        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            log.info(f"[MJPEG Cam#{id_camara}] Cliente desconectado")

    return StreamingResponse(
        generar_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

@router.get("/test-frame/{id_camara}")
async def test_frame(
    id_camara: int,
    _admin: Administrador = Depends(get_current_admin),
):
    worker = rtsp_manager._workers.get(id_camara)
    if not worker:
        return {"error": "Worker no existe"}
    return {
        "activo": worker.activo,
        "tiene_jpg": worker.ultimo_jpg is not None,
        "tamanio_jpg": len(worker.ultimo_jpg) if worker.ultimo_jpg else 0,
        "ultimo_frame_ts": worker.ultimo_frame_ts,
    }