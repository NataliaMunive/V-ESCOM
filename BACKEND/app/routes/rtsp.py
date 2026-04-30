"""
Router de Gestión de Streams RTSP - V-ESCOM (CU06)
===================================================
Permite arrancar y detener la captura continua de cámaras desde el frontend,
y consultar el estado actual de cada worker.

Endpoints:
  POST  /rtsp/iniciar         — Arranca un worker para una cámara
  DELETE /rtsp/detener/{id}   — Detiene el worker de una cámara
  GET   /rtsp/estado          — Estado de todos los workers activos
"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.camara import Camara
from app.services.rtsp_manager import rtsp_manager

router = APIRouter(prefix="/rtsp", tags=["RTSP / Captura Continua"])


# ─── Schemas inline (simples, sin archivo separado) ──────────────────────────
from pydantic import BaseModel


class IniciarStreamPayload(BaseModel):
    id_camara: int
    rtsp_url: Optional[str] = None      # Si None, se construye desde la IP de la BD
    rtsp_user: Optional[str] = "admin"
    rtsp_pass: Optional[str] = ""
    stream: Optional[str] = "stream2"   # stream1 = 2K, stream2 = SD (más rápido)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/iniciar", summary="Iniciar captura continua de una cámara")
async def iniciar_stream(
    payload: IniciarStreamPayload,
    db: Session = Depends(get_db),
    admin: Administrador = Depends(get_current_admin),
):
    """
    Arranca el worker de captura RTSP para la cámara indicada.
    
    Si no se proporciona rtsp_url, se construye automáticamente
    usando la dirección IP registrada en la tabla `camaras`.
    
    Ejemplo de URL para MC210:
      rtsp://admin:tucontraseña@192.168.1.64:554/stream2
    """
    # Resolver URL
    rtsp_url = payload.rtsp_url

    if not rtsp_url:
        camara = db.query(Camara).filter(
            Camara.id_camara == payload.id_camara
        ).first()

        if not camara:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Cámara no encontrada")

        if not camara.direccion_ip:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail="La cámara no tiene dirección IP configurada. "
                       "Actualízala en Gestión de Cámaras o proporciona rtsp_url.",
            )

        user = payload.rtsp_user or "admin"
        pwd  = payload.rtsp_pass or ""
        if pwd:
            rtsp_url = (
                f"rtsp://{user}:{pwd}@{camara.direccion_ip}:554/{payload.stream}"
            )
        else:
            rtsp_url = f"rtsp://{camara.direccion_ip}:554/{payload.stream}"

    # Inyectar token del admin actual para que el worker lo use
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(admin.id_admin), "email": admin.email})
    rtsp_manager.set_token(token)

    await rtsp_manager.iniciar_camara(payload.id_camara, rtsp_url)

    return {
        "mensaje": f"Worker iniciado para cámara #{payload.id_camara}",
        "rtsp_url": rtsp_url,
    }


@router.delete("/detener/{id_camara}", summary="Detener captura de una cámara")
def detener_stream(
    id_camara: int,
    _admin: Administrador = Depends(get_current_admin),
):
    """Detiene el worker de captura continua de la cámara especificada."""
    rtsp_manager.detener_camara(id_camara)
    return {"mensaje": f"Worker detenido para cámara #{id_camara}"}


@router.get("/estado", summary="Estado de los workers RTSP activos")
def estado_streams(
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Retorna el estado de todos los workers de captura activos,
    incluyendo el último resultado de reconocimiento de cada uno.
    """
    return rtsp_manager.estado()


@router.get("/snapshot/{id_camara}", summary="Captura un frame JPEG de la cámara")
async def snapshot(
    id_camara: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Conecta al stream RTSP, captura un frame y lo devuelve como JPEG.
    No requiere FFmpeg — usa OpenCV directamente.
    """
    import asyncio
    import cv2
    import os
    from fastapi import HTTPException
    from fastapi.responses import Response

    # Obtener URL del worker activo o construirla desde la BD
    worker = rtsp_manager._workers.get(id_camara)
    if worker and worker.activo:
        rtsp_url = worker.rtsp_url
    else:
        camara = db.query(Camara).filter(Camara.id_camara == id_camara).first()
        if not camara or not camara.direccion_ip:
            raise HTTPException(status_code=404, detail="Cámara no encontrada o sin IP")
        user = os.getenv("RTSP_USER", "admin")
        pwd  = os.getenv("RTSP_PASS", "")
        rtsp_url = (
            f"rtsp://{user}:{pwd}@{camara.direccion_ip}:554/stream2"
            if pwd else
            f"rtsp://{camara.direccion_ip}:554/stream2"
        )

    def _capturar() -> bytes:
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            return b""
        for _ in range(5):   # vaciar buffer inicial para no recibir frame negro
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return b""
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ok else b""

    jpg = await asyncio.get_event_loop().run_in_executor(None, _capturar)

    if not jpg:
        raise HTTPException(
            status_code=503,
            detail="No se pudo capturar frame. Verifica que la cámara esté encendida y en red."
        )

    return Response(content=jpg, media_type="image/jpeg")