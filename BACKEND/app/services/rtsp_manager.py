"""
Servicio de Gestión de Workers RTSP - V-ESCOM
=============================================
Usa threading para OpenCV (bloqueante) + asyncio para el análisis de IA.
"""
from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
import time
from typing import Dict, Optional

import cv2

log = logging.getLogger("rtsp_manager")

INTERVALO_SEG  = float(os.getenv("RTSP_INTERVALO_SEG", "3"))
MAX_REINTENTOS = int(os.getenv("RTSP_REINTENTOS", "5"))
ESPERA_RETRY   = 8


class CameraWorker:
    """
    Worker de captura RTSP.
    - Thread de captura: Lee frames con OpenCV (bloqueante) en hilo separado.
    - Task asyncio de análisis: Toma frames de la queue y llama a InsightFace.
    """

    def __init__(self, id_camara: int, rtsp_url: str) -> None:
        self.id_camara            = id_camara
        self.rtsp_url             = rtsp_url
        self.activo               = False
        self.ultimo_resultado: Optional[dict] = None
        self.ultimo_frame_ts: float = 0.0
        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._capture_thread: Optional[threading.Thread] = None
        self._analysis_task: Optional[asyncio.Task] = None

    # ── Thread de captura (OpenCV) ────────────────────────────────────────────
    def _capture_loop(self) -> None:
        """Corre en un thread OS — lee frames y los mete en la queue."""
        reintentos = 0
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

        while self.activo and reintentos <= MAX_REINTENTOS:
            log.info(f"[Cam#{self.id_camara}] Conectando a {self.rtsp_url} ...")
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)  # type: ignore
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # type: ignore

            if not cap.isOpened():
                reintentos += 1
                log.warning(
                    f"[Cam#{self.id_camara}] No se pudo abrir stream "
                    f"(intento {reintentos}/{MAX_REINTENTOS})"
                )
                time.sleep(ESPERA_RETRY)
                continue

            reintentos = 0
            ultimo_envio = 0.0
            log.info(f"[Cam#{self.id_camara}] ✓ Stream abierto")

            while self.activo:
                ret, frame = cap.read()
                if not ret:
                    log.warning(f"[Cam#{self.id_camara}] Frame perdido.")
                    break

                ahora = time.monotonic()
                if ahora - ultimo_envio < INTERVALO_SEG:
                    continue  # No dormir — seguir vaciando el buffer de la cámara

                ultimo_envio = ahora

                try:
                    ok, buf = cv2.imencode(  # type: ignore
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                    )
                    if not ok:
                        continue
                    jpg = buf.tobytes()
                    # Descartar frame viejo si la queue está llena
                    if self._frame_queue.full():
                        try:
                            self._frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self._frame_queue.put_nowait(jpg)
                except Exception as e:
                    log.debug(f"[Cam#{self.id_camara}] Error encode: {e}")

            cap.release()
            if self.activo:
                reintentos += 1
                log.warning(
                    f"[Cam#{self.id_camara}] Reintentando en {ESPERA_RETRY}s ..."
                )
                time.sleep(ESPERA_RETRY)

        self.activo = False
        log.info(f"[Cam#{self.id_camara}] Thread de captura finalizado.")

    # ── Task asyncio de análisis (InsightFace) ────────────────────────────────
    async def _analysis_loop(self) -> None:
        """Corre en el loop de asyncio — toma frames y llama al servicio de IA."""
        from app.bd import SessionLocal
        from app.services.reconocimiento_service import identificar_rostro

        log.info(f"[Cam#{self.id_camara}] Task de análisis iniciada.")

        while self.activo:
            # Esperar frame sin bloquear el loop
            try:
                jpg = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._frame_queue.get(timeout=2)
                )
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

            self.ultimo_frame_ts = time.time()
            log.info(f"[Cam#{self.id_camara}] Analizando frame...")

            class _FakeUpload:
                filename = "frame.jpg"
                content_type = "image/jpeg"
                _data = jpg

                async def read(self):
                    return self._data

            db = SessionLocal()
            try:
                resultado = await identificar_rostro(
                    db, _FakeUpload(), id_camara=self.id_camara
                )
                self.ultimo_resultado = {
                    "tipo_acceso": resultado.tipo_acceso,
                    "similitud":   resultado.similitud,
                    "nombre":      resultado.nombre,
                    "apellidos":   resultado.apellidos,
                    "id_evento":   resultado.id_evento,
                }
                nivel = "✓" if resultado.tipo_acceso == "Autorizado" else "⚠"
                log.info(
                    f"[Cam#{self.id_camara}] {nivel} {resultado.tipo_acceso} "
                    f"sim={resultado.similitud:.3f} evento=#{resultado.id_evento}"
                )
            except Exception as e:
                msg = str(e)
                if "422" in msg or "rostro" in msg.lower() or "No se detectó" in msg:
                    log.debug(f"[Cam#{self.id_camara}] Sin rostro detectable.")
                else:
                    import traceback
                    log.warning(f"[Cam#{self.id_camara}] Error en identificación: {e}\n{traceback.format_exc()}")
            finally:
                db.close()

        log.info(f"[Cam#{self.id_camara}] Task de análisis finalizada.")

    # ── Control ───────────────────────────────────────────────────────────────
    async def iniciar_async(self, token: str) -> None:
        if self.activo:
            return
        self.activo = True

        # Arrancar thread de captura
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name=f"rtsp-cam-{self.id_camara}",
            daemon=True,
        )
        self._capture_thread.start()

        # Arrancar task de análisis en el loop actual
        self._analysis_task = asyncio.create_task(self._analysis_loop())
        await asyncio.sleep(0)  # ceder control para que la task arranque
        log.info(f"[Cam#{self.id_camara}] Worker completo iniciado.")

    def detener(self) -> None:
        self.activo = False
        if self._analysis_task:
            self._analysis_task.cancel()
        # El thread se detendrá solo al ver activo=False
        log.info(f"[Cam#{self.id_camara}] Worker detenido.")


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
            await asyncio.sleep(0.5)  # dar tiempo para limpiar
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
                "id_camara":          wid,
                "activo":             w.activo,
                "rtsp_url":           w.rtsp_url,
                "ultimo_frame_ts":    w.ultimo_frame_ts,
                "ultimo_resultado":   w.ultimo_resultado,
            }
            for wid, w in self._workers.items()
        ]

    def inicializar(self, app) -> None:  # type: ignore[type-arg]
        @app.on_event("startup")
        async def _startup() -> None:
            await self._arrancar_camaras_activas()

        @app.on_event("shutdown")
        async def _shutdown() -> None:
            self.detener_todas()

    async def _arrancar_camaras_activas(self) -> None:
        """Auto-arranca workers para cámaras activas con IP configurada."""
        from app.bd import SessionLocal
        from app.models.camara import Camara
        from app.core.security import create_access_token
        from app.models.administrador import Administrador

        db = SessionLocal()
        try:
            admin = db.query(Administrador).filter(
                Administrador.activo.is_(True)
            ).first()
            if admin:
                self._token = create_access_token(
                    {"sub": str(admin.id_admin), "email": admin.email}
                )

            camaras = (
                db.query(Camara)
                .filter(Camara.activa.is_(True))
                .filter(Camara.direccion_ip.isnot(None))
                .all()
            )

            for cam in camaras:
                rtsp_url = os.getenv(f"RTSP_URL_{cam.id_camara}")
                if not rtsp_url and cam.direccion_ip:
                    user = os.getenv("RTSP_USER", "admin")
                    pwd  = os.getenv("RTSP_PASS", "")
                    rtsp_url = (
                        f"rtsp://{user}:{pwd}@{cam.direccion_ip}:554/stream2"
                        if pwd else
                        f"rtsp://{cam.direccion_ip}:554/stream2"
                    )
                if rtsp_url:
                    log.info(
                        f"Auto-arrancando cámara #{cam.id_camara} → {rtsp_url}"
                    )
                    await self.iniciar_camara(cam.id_camara, rtsp_url)

        except Exception as e:
            log.error(f"Error al arrancar workers: {e}")
        finally:
            db.close()


# Instancia global
rtsp_manager = RTSPManager()