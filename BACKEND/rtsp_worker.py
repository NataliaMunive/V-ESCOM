"""
Motor de Captura RTSP Continua - V-ESCOM (CU06)
================================================
Worker asíncrono que:
  1. Lee frames del stream RTSP de la MC210.
  2. Detecta rostros con InsightFace cada N segundos (configurable).
  3. Llama al servicio de reconocimiento ya existente.
  4. Publica alertas en tiempo real vía WebSocket.

URL RTSP de la MERCUSYS MC210:
  Stream principal (2K): rtsp://<user>:<pass>@<ip>:554/stream1
  Stream secundario (SD): rtsp://<user>:<pass>@<ip>:554/stream2

Uso:
  python rtsp_worker.py --camara-id 1 --rtsp-url "rtsp://admin:pass@192.168.1.64:554/stream1"

O desde .env:
  RTSP_URL_1=rtsp://admin:pass@192.168.1.64:554/stream1
  RTSP_INTERVALO_SEG=3   # segundos entre análisis (default 3)
  RTSP_REINTENTOS=5      # reconexiones antes de rendirse
"""
from __future__ import annotations

import argparse
import asyncio
import io
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import httpx
from dotenv import load_dotenv

# ─── Configuración de logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] RTSP-Worker | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rtsp_worker")

# Cargar .env del directorio del backend
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# ─── Constantes ───────────────────────────────────────────────────────────────
API_BASE        = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TOKEN       = os.getenv("RTSP_API_TOKEN", "")          # JWT de admin
INTERVALO_SEG   = float(os.getenv("RTSP_INTERVALO_SEG", "3"))
MAX_REINTENTOS  = int(os.getenv("RTSP_REINTENTOS", "5"))
ESPERA_REINTENTO = 8   # segundos entre reconexiones


# ─── Autenticación automática ─────────────────────────────────────────────────
async def obtener_token() -> str:
    """Inicia sesión como admin para obtener JWT. Usa vars de entorno."""
    email    = os.getenv("ADMIN_EMAIL", "admin@ipn.mx")
    password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    async with httpx.AsyncClient(base_url=API_BASE) as client:
        r = await client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        log.info("✓ Token JWT obtenido")
        return token


# ─── Envío de frame al endpoint de identificación ────────────────────────────
async def identificar_frame(
    frame_jpg: bytes,
    id_camara: int,
    token: str,
) -> Optional[dict]:
    """Envía un frame JPEG a POST /reconocimiento/identificar y retorna el resultado."""
    headers = {"Authorization": f"Bearer {token}"}
    files   = {"imagen": ("frame.jpg", io.BytesIO(frame_jpg), "image/jpeg")}
    data    = {"id_camara": str(id_camara)}

    async with httpx.AsyncClient(base_url=API_BASE, timeout=15) as client:
        try:
            r = await client.post(
                "/reconocimiento/identificar",
                headers=headers,
                files=files,
                data=data,
            )
            if r.status_code == 422:
                # Sin rostro detectable — normal, no es un error
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            log.warning(f"HTTP {e.response.status_code} al identificar frame: {e.response.text[:200]}")
            return None
        except Exception as e:
            log.error(f"Error enviando frame: {e}")
            return None


def frame_a_jpg(frame) -> bytes:
    """Codifica un array BGR de OpenCV a JPEG en memoria."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("No se pudo codificar el frame como JPEG")
    return buf.tobytes()


# ─── Loop principal de captura ────────────────────────────────────────────────
async def capturar_y_analizar(rtsp_url: str, id_camara: int, token: str) -> None:
    """
    Abre el stream RTSP y analiza un frame cada INTERVALO_SEG segundos.
    Se reconecta automáticamente si el stream se interrumpe.
    """
    reintentos = 0

    while reintentos <= MAX_REINTENTOS:
        log.info(f"Conectando a {rtsp_url}  (cámara #{id_camara}) ...")

        # Forzar uso de TCP en lugar de UDP para mejor estabilidad en WiFi
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)          # buffer mínimo = menos latencia
        # Algunos builds de OpenCV requieren esta env var para TCP:
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

        if not cap.isOpened():
            reintentos += 1
            log.warning(f"No se pudo abrir el stream (intento {reintentos}/{MAX_REINTENTOS}). "
                        f"Esperando {ESPERA_REINTENTO}s ...")
            await asyncio.sleep(ESPERA_REINTENTO)
            continue

        log.info(f"✓ Stream abierto — analizando cada {INTERVALO_SEG}s")
        reintentos = 0           # reset en caso de reconexión exitosa
        ultimo_analisis = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                log.warning("Frame perdido — posible desconexión del stream.")
                break

            ahora = time.monotonic()
            if ahora - ultimo_analisis < INTERVALO_SEG:
                # Seguimos leyendo para vaciar el buffer, sin analizar
                await asyncio.sleep(0.01)
                continue

            ultimo_analisis = ahora

            try:
                jpg = frame_a_jpg(frame)
            except ValueError as e:
                log.debug(f"Encode error: {e}")
                continue

            resultado = await identificar_frame(jpg, id_camara, token)

            if resultado:
                acceso  = resultado.get("tipo_acceso", "?")
                sim     = resultado.get("similitud", 0)
                nombre  = resultado.get("nombre") or "Desconocido"
                id_ev   = resultado.get("id_evento", "?")
                nivel   = "✓" if acceso == "Autorizado" else "⚠"
                log.info(
                    f"{nivel} [{acceso}]  {nombre}  "
                    f"similitud={sim:.3f}  evento=#{id_ev}  cámara=#{id_camara}"
                )
            else:
                log.debug("Sin rostro detectable en este frame.")

        cap.release()
        reintentos += 1
        log.warning(f"Stream cerrado. Reintentando en {ESPERA_REINTENTO}s "
                    f"(intento {reintentos}/{MAX_REINTENTOS}) ...")
        await asyncio.sleep(ESPERA_REINTENTO)

    log.error(f"Se agotaron los reintentos para cámara #{id_camara}. Worker terminado.")


# ─── Punto de entrada ─────────────────────────────────────────────────────────
async def main() -> None:
    parser = argparse.ArgumentParser(description="V-ESCOM RTSP Worker")
    parser.add_argument("--camara-id",  type=int, required=True,
                        help="ID de la cámara en la BD (tabla camaras.id_camara)")
    parser.add_argument("--rtsp-url",   type=str, default=None,
                        help="URL RTSP completa. Si no se indica, se lee de RTSP_URL_<id>")
    parser.add_argument("--token",      type=str, default=None,
                        help="JWT de admin. Si no se indica, el worker hace login automático.")
    args = parser.parse_args()

    # Resolver URL RTSP
    rtsp_url = args.rtsp_url or os.getenv(f"RTSP_URL_{args.camara_id}")
    if not rtsp_url:
        log.error(f"No se encontró URL RTSP. Define --rtsp-url o RTSP_URL_{args.camara_id} en .env")
        sys.exit(1)

    # Resolver token
    token = args.token or API_TOKEN
    if not token:
        token = await obtener_token()

    await capturar_y_analizar(rtsp_url, args.camara_id, token)


if __name__ == "__main__":
    asyncio.run(main())