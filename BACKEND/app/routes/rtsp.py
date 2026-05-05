"""
Router de Gestión de Streams RTSP - V-ESCOM (CU06)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import cv2
import os
import logging

from app.bd import get_db
from app.core.deps import get_current_admin
from app.core.security import decode_access_token
from app.models.administrador import Administrador
from app.models.camara import Camara
from app.services.rtsp_manager import rtsp_manager
from pydantic import BaseModel

log = logging.getLogger("rtsp_routes")
router = APIRouter(prefix="/rtsp", tags=["RTSP / Captura Continua"])


class IniciarStreamPayload(BaseModel):
    id_camara: int
    rtsp_url: Optional[str] = None
    rtsp_user: Optional[str] = "adminadmin"
    rtsp_pass: Optional[str] = ""
    stream: Optional[str] = "stream2"


def _resolver_rtsp_url(id_camara: int, db: Session,
                        user: str = "adminadmin", pwd: str = "",
                        stream: str = "stream2") -> str:
    worker = rtsp_manager._workers.get(id_camara)
    if worker and worker.activo:
        return worker.rtsp_url
    camara = db.query(Camara).filter(Camara.id_camara == id_camara).first()
    if not camara or not camara.direccion_ip:
        raise HTTPException(status_code=404, detail="Cámara no encontrada o sin IP")
    env_user = os.getenv("RTSP_USER", user)
    env_pwd  = os.getenv("RTSP_PASS", pwd)
    if env_pwd:
        return f"rtsp://{env_user}:{env_pwd}@{camara.direccion_ip}:554/{stream}"
    return f"rtsp://{camara.direccion_ip}:554/{stream}"


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
            raise HTTPException(status_code=422, detail="La cámara no tiene IP configurada.")
        user = payload.rtsp_user or "adminadmin"
        pwd  = payload.rtsp_pass or ""
        rtsp_url = (
            f"rtsp://{user}:{pwd}@{camara.direccion_ip}:554/{payload.stream}"
            if pwd else
            f"rtsp://{camara.direccion_ip}:554/{payload.stream}"
        )
    log.info(f"URL RTSP que se usará: {rtsp_url}")
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(admin.id_admin), "email": admin.email})
    rtsp_manager.set_token(token)
    await rtsp_manager.iniciar_camara(payload.id_camara, rtsp_url)
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
    rtsp_url = _resolver_rtsp_url(id_camara, db)

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

    # Verificar que el worker existe y está activo
    worker = rtsp_manager._workers.get(id_camara)
    if not worker or not worker.activo:
        raise HTTPException(status_code=503, detail="Stream no activo. Inicia el worker primero.")

    log.info(f"[MJPEG Cam#{id_camara}] Cliente conectado")

    async def generar_frames():
        """
        Lee ultimo_jpg del worker directamente.
        NO abre conexión RTSP — evita conflicto con el worker de captura.
        """
        ultimo_enviado = None
        sin_frame = 0

        try:
            while worker.activo:
                jpg = worker.ultimo_jpg

                if jpg is not None and jpg is not ultimo_enviado:
                    ultimo_enviado = jpg
                    sin_frame = 0
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + jpg
                        + b"\r\n"
                    )
                else:
                    sin_frame += 1
                    if sin_frame > 150:  # ~10s sin frames nuevos
                        log.warning(f"[MJPEG Cam#{id_camara}] Sin frames nuevos, cerrando")
                        break

                await asyncio.sleep(0.067)  # ~15 fps

        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            log.info(f"[MJPEG Cam#{id_camara}] Cliente desconectado")

    return StreamingResponse(
        generar_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
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