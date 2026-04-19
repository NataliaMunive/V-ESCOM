"""
CU06: Captura continua desde stream RTSP/IP - V-ESCOM

Gestiona el monitoreo automático de cámaras IP usando OpenCV para capturar
frames y el motor ArcFace/InsightFace para identificar rostros en tiempo real.

Flujo:
    1. Se inicia el monitoreo de una cámara registrada en BD.
    2. Cada N segundos se captura un frame del stream RTSP.
    3. El frame se procesa con el motor de reconocimiento facial.
    4. Si se detecta un intruso, se genera alerta + SMS + WebSocket.
"""
import asyncio
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.bd import get_db, SessionLocal
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.camara import Camara
from app.services import reconocimiento_service

router = APIRouter(prefix="/stream", tags=["Stream RTSP"])

# ─── Estado global de tareas activas ────────────────────────────────────────
# { id_camara: asyncio.Task }
_tareas_activas: dict[int, asyncio.Task] = {}


# ─── Clase auxiliar para simular UploadFile con bytes de frame ───────────────
class FrameUpload:
    """
    Simula el objeto UploadFile de FastAPI para pasar frames
    capturados por OpenCV al servicio de reconocimiento.
    """
    def __init__(self, contenido: bytes):
        self.filename = "frame.jpg"
        self._contenido = contenido

    async def read(self) -> bytes:
        return self._contenido


# ─── Tarea de captura en background ──────────────────────────────────────────
async def _capturar_camara(
    id_camara: int,
    url_stream: str,
    intervalo: float = 3.0,
):
    """
    Tarea asyncio que captura frames continuamente desde una cámara IP.
    Se ejecuta en background mientras el monitoreo esté activo.

    Args:
        id_camara: ID de la cámara en BD (para registrar eventos).
        url_stream: URL RTSP/HTTP del stream o índice de webcam ("0").
        intervalo: Segundos entre cada captura de frame.
    """
    # Convertir "0" a entero para webcam local
    fuente = int(url_stream) if url_stream.isdigit() else url_stream

    cap = cv2.VideoCapture(fuente)

    if not cap.isOpened():
        print(f"[Stream #{id_camara}] ✗ No se pudo abrir: {url_stream}")
        _tareas_activas.pop(id_camara, None)
        return

    print(f"[Stream #{id_camara}] ✓ Monitoreo iniciado → {url_stream}")

    intentos_fallidos = 0
    MAX_INTENTOS = 5

    try:
        while id_camara in _tareas_activas:
            ret, frame = cap.read()

            if not ret:
                intentos_fallidos += 1
                print(
                    f"[Stream #{id_camara}] Sin frame "
                    f"({intentos_fallidos}/{MAX_INTENTOS}), reintentando..."
                )

                if intentos_fallidos >= MAX_INTENTOS:
                    print(
                        f"[Stream #{id_camara}] Demasiados fallos, "
                        f"reconectando stream..."
                    )
                    cap.release()
                    await asyncio.sleep(5)
                    cap = cv2.VideoCapture(fuente)
                    intentos_fallidos = 0

                await asyncio.sleep(intervalo)
                continue

            intentos_fallidos = 0

            # Convertir frame BGR → bytes JPEG
            _, buffer = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            imagen_bytes = buffer.tobytes()

            # Procesar con el motor de reconocimiento en una sesión nueva
            db: Session = SessionLocal()
            try:
                resultado = await reconocimiento_service.identificar_rostro(
                    db,
                    FrameUpload(imagen_bytes),
                    id_camara=id_camara,
                )
                estado = "✓ Autorizado" if resultado.tipo_acceso == "Autorizado" else "⚠ INTRUSO"
                print(
                    f"[Stream #{id_camara}] {estado} | "
                    f"similitud={resultado.similitud:.3f} | "
                    f"evento=#{resultado.id_evento}"
                )
            except ValueError:
                # No se detectó rostro en el frame — es normal, no es error
                pass
            except Exception as e:
                print(f"[Stream #{id_camara}] Error procesando frame: {e}")
            finally:
                db.close()

            await asyncio.sleep(intervalo)

    except asyncio.CancelledError:
        print(f"[Stream #{id_camara}] Tarea cancelada correctamente.")
    finally:
        cap.release()
        _tareas_activas.pop(id_camara, None)
        print(f"[Stream #{id_camara}] Stream cerrado y recursos liberados.")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/{id_camara}/iniciar",
    summary="Iniciar monitoreo continuo de una cámara IP",
)
async def iniciar_stream(
    id_camara: int,
    intervalo: float = 3.0,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Inicia la captura continua de frames desde la cámara registrada.

    - La URL del stream se toma del campo `direccion_ip` de la cámara en BD.
    - Puedes guardar la URL RTSP completa en ese campo al registrar la cámara.
    - Para usar la webcam local de prueba, guarda "0" como dirección IP.
    - El parámetro `intervalo` controla los segundos entre capturas (default: 3).
    """
    camara = db.query(Camara).filter(
        Camara.id_camara == id_camara,
        Camara.activa.is_(True),
    ).first()

    if not camara:
        raise HTTPException(
            status_code=404,
            detail="Cámara no encontrada o inactiva"
        )

    if id_camara in _tareas_activas:
        raise HTTPException(
            status_code=409,
            detail="Esta cámara ya está siendo monitoreada"
        )

    if not camara.direccion_ip:
        raise HTTPException(
            status_code=422,
            detail=(
                "La cámara no tiene dirección IP/URL configurada. "
                "Edítala y agrega la URL RTSP o '0' para webcam local."
            ),
        )

    url_stream = camara.direccion_ip

    # Crear tarea asyncio en background
    tarea = asyncio.create_task(
        _capturar_camara(id_camara, url_stream, intervalo)
    )
    _tareas_activas[id_camara] = tarea

    return {
        "message": f"Monitoreo iniciado para cámara '{camara.nombre}' (#{id_camara})",
        "url_stream": url_stream,
        "intervalo_segundos": intervalo,
        "estado": "activo",
    }


@router.post(
    "/{id_camara}/detener",
    summary="Detener monitoreo de una cámara",
)
async def detener_stream(
    id_camara: int,
    _admin: Administrador = Depends(get_current_admin),
):
    """Cancela la tarea de captura y libera los recursos de la cámara."""
    if id_camara not in _tareas_activas:
        raise HTTPException(
            status_code=404,
            detail="Esta cámara no está siendo monitoreada actualmente"
        )

    tarea = _tareas_activas.pop(id_camara)
    tarea.cancel()

    return {
        "message": f"Monitoreo detenido para cámara #{id_camara}",
        "estado": "inactivo",
    }


@router.get(
    "/activas",
    summary="Listar cámaras en monitoreo activo",
)
async def listar_activas(
    _admin: Administrador = Depends(get_current_admin),
):
    """Retorna los IDs de las cámaras actualmente siendo monitoreadas."""
    return {
        "camaras_activas": list(_tareas_activas.keys()),
        "total": len(_tareas_activas),
    }


@router.get(
    "/estado/{id_camara}",
    summary="Verificar estado de monitoreo de una cámara",
)
async def estado_stream(
    id_camara: int,
    _admin: Administrador = Depends(get_current_admin),
):
    """Verifica si una cámara específica está siendo monitoreada."""
    activa = id_camara in _tareas_activas
    return {
        "id_camara": id_camara,
        "monitoreando": activa,
        "estado": "activo" if activa else "inactivo",
    }