"""
Servicio de Gestión de Workers RTSP - V-ESCOM
=============================================
Administra el ciclo de vida de los procesos de captura continua.
Permite arrancar/detener workers por cámara desde la API de FastAPI.

Integración en main.py:
  from app.services.rtsp_manager import rtsp_manager
  rtsp_manager.inicializar(app)   # llama a @app.on_event("startup")
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import time
from typing import Dict, Optional

import cv2

log = logging.getLogger("rtsp_manager")

INTERVALO_SEG  = float(os.getenv("RTSP_INTERVALO_SEG", "3"))
MAX_REINTENTOS = int(os.getenv("RTSP_REINTENTOS", "5"))
ESPERA_RETRY   = 8


class CameraWorker:
    """Encapsula la tarea asyncio de un stream RTSP activo."""

    def __init__(self, id_camara: int, rtsp_url: str) -> None:
        self.id_camara  = id_camara
        self.rtsp_url   = rtsp_url
        self.activo     = False
        self.ultimo_resultado: Optional[dict] = None
        self.ultimo_frame_ts: float = 0.0
        self._task: Optional[asyncio.Task] = None

    def iniciar(self, token: str) -> None:
        if self._task and not self._task.done():
            return
        self.activo = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._loop(token))
        except RuntimeError:
            # No hay loop corriendo — obtener el loop principal de la app
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._loop(token))
        log.info(f"Worker iniciado para cámara #{self.id_camara}")
    
    async def iniciar_async(self, token: str) -> None:
        if self._task and not self._task.done():
            return
        self.activo = True
        self._task = asyncio.create_task(self._loop(token))
        log.info(f"Worker iniciado para cámara #{self.id_camara}")

    def detener(self) -> None:
        self.activo = False
        if self._task:
            self._task.cancel()
        log.info(f"Worker detenido para cámara #{self.id_camara}")

    async def _loop(self, token: str) -> None:
        """Loop de captura y análisis para esta cámara."""
        # Import aquí para evitar dependencias circulares
        from app.bd import SessionLocal
        from app.services.reconocimiento_service import identificar_rostro
        from fastapi import UploadFile
        import httpx

        reintentos = 0

        while self.activo and reintentos <= MAX_REINTENTOS:
            log.info(f"[Cam#{self.id_camara}] Conectando a {self.rtsp_url} ...")

            os.environ.setdefault(
                "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp"
            )
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                reintentos += 1
                log.warning(
                    f"[Cam#{self.id_camara}] No se pudo abrir stream "
                    f"(intento {reintentos}/{MAX_REINTENTOS})"
                )
                await asyncio.sleep(ESPERA_RETRY)
                continue

            reintentos = 0
            ultimo_analisis = 0.0
            log.info(f"[Cam#{self.id_camara}] ✓ Stream abierto")

            while self.activo:
                ret, frame = cap.read()
                if not ret:
                    log.warning(f"[Cam#{self.id_camara}] Frame perdido.")
                    break

                ahora = time.monotonic()
                if ahora - ultimo_analisis < INTERVALO_SEG:
                    await asyncio.sleep(0.02)
                    continue

                ultimo_analisis = ahora
                self.ultimo_frame_ts = time.time()

                try:
                    ok, buf = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                    )
                    if not ok:
                        continue
                    jpg_bytes = buf.tobytes()
                except Exception:
                    continue

                # Crear un UploadFile falso que el servicio pueda leer
                class _FakeUpload:
                    filename = "frame.jpg"
                    content_type = "image/jpeg"
                    _data = jpg_bytes

                    async def read(self):
                        return self._data

                db = SessionLocal()
                try:
                    resultado = await identificar_rostro(
                        db, _FakeUpload(), id_camara=self.id_camara
                    )
                    self.ultimo_resultado = resultado.__dict__
                    nivel = "✓" if resultado.tipo_acceso == "Autorizado" else "⚠"
                    log.info(
                        f"[Cam#{self.id_camara}] {nivel} {resultado.tipo_acceso} "
                        f"sim={resultado.similitud:.3f} evento=#{resultado.id_evento}"
                    )
                except Exception as e:
                    # 422 = sin rostro; es esperado, no loguear como error
                    if "422" not in str(e) and "rostro" not in str(e).lower():
                        log.debug(f"[Cam#{self.id_camara}] Sin rostro detectable: {e}")
                finally:
                    db.close()

            cap.release()
            if self.activo:
                reintentos += 1
                log.warning(
                    f"[Cam#{self.id_camara}] Reintentando en {ESPERA_RETRY}s ..."
                )
                await asyncio.sleep(ESPERA_RETRY)

        self.activo = False
        log.info(f"[Cam#{self.id_camara}] Worker finalizado.")


class RTSPManager:
    """Singleton que gestiona todos los workers de cámaras activas."""

    def __init__(self) -> None:
        self._workers: Dict[int, CameraWorker] = {}
        self._token: str = ""

    def set_token(self, token: str) -> None:
        self._token = token

    async def iniciar_camara(self, id_camara: int, rtsp_url: str) -> None:
        if id_camara in self._workers:
            self._workers[id_camara].detener()
        worker = CameraWorker(id_camara, rtsp_url)
        self._workers[id_camara] = worker
        await worker.iniciar_async(self._token)

    def detener_camara(self, id_camara: int) -> None:
        if id_camara in self._workers:
            self._workers[id_camara].detener()
            del self._workers[id_camara]

    def detener_todas(self) -> None:
        for w in self._workers.values():
            w.detener()
        self._workers.clear()

    def estado(self) -> list[dict]:
        return [
            {
                "id_camara": wid,
                "activo": w.activo,
                "rtsp_url": w.rtsp_url,
                "ultimo_frame_ts": w.ultimo_frame_ts,
                "ultimo_resultado": w.ultimo_resultado,
            }
            for wid, w in self._workers.items()
        ]

    def inicializar(self, app) -> None:  # type: ignore[type-arg]
        """
        Registra eventos startup/shutdown en la app FastAPI.
        Llama a esto en main.py: rtsp_manager.inicializar(app)
        """
        from fastapi import FastAPI

        @app.on_event("startup")
        async def _startup() -> None:
            await self._arrancar_camaras_activas()

        @app.on_event("shutdown")
        async def _shutdown() -> None:
            self.detener_todas()

    async def _arrancar_camaras_activas(self) -> None:
        """Al iniciar la API, arranca workers para todas las cámaras con URL RTSP."""
        from app.bd import SessionLocal
        from app.models.camara import Camara
        from app.core.security import create_access_token
        from app.models.administrador import Administrador

        db = SessionLocal()
        try:
            # Generar token interno de sistema para los workers
            admin = db.query(Administrador).filter(
                Administrador.activo.is_(True)
            ).first()
            if admin:
                token = create_access_token(
                    {"sub": str(admin.id_admin), "email": admin.email}
                )
                self._token = token

            camaras = (
                db.query(Camara)
                .filter(Camara.activa.is_(True))
                .filter(Camara.direccion_ip.isnot(None))
                .all()
            )

            for cam in camaras:
                # Solo arrancar si tiene URL RTSP en .env o si la IP está configurada
                rtsp_url = os.getenv(f"RTSP_URL_{cam.id_camara}")
                if not rtsp_url and cam.direccion_ip:
                    # Construir URL por defecto con credenciales del .env
                    user = os.getenv("RTSP_USER", "admin")
                    pwd  = os.getenv("RTSP_PASS", "")
                    if pwd:
                        rtsp_url = f"rtsp://{user}:{pwd}@{cam.direccion_ip}:554/stream2"
                    else:
                        rtsp_url = f"rtsp://{cam.direccion_ip}:554/stream2"

                if rtsp_url:
                    log.info(
                        f"Auto-arrancando worker para cámara #{cam.id_camara} "
                        f"({cam.nombre}) → {rtsp_url}"
                    )
                    await self.iniciar_camara(cam.id_camara, rtsp_url)

        except Exception as e:
            log.error(f"Error al arrancar workers de cámaras: {e}")
        finally:
            db.close()


# Instancia global (importar desde otros módulos)
rtsp_manager = RTSPManager()