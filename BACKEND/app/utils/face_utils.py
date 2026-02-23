"""
Utilidades de reconocimiento facial usando InsightFace (ArcFace).
- Detección de rostros con OpenCV/InsightFace.
- Extracción de embeddings de 512 dimensiones.
- Normalización L2 para comparación por similitud coseno.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

# InsightFace se inicializa una sola vez al importar el módulo
try:
    from insightface.app import FaceAnalysis

    _face_app: Optional[FaceAnalysis] = None

    def _get_face_app() -> FaceAnalysis:
        global _face_app
        if _face_app is None:
            # buffalo_l = ArcFace R100 + RetinaFace (detector)
            _face_app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],  # cambia a CUDAExecutionProvider si tienes GPU
            )
            _face_app.prepare(ctx_id=0, det_size=(640, 640))
        return _face_app

    INSIGHTFACE_DISPONIBLE = True

except ImportError:
    INSIGHTFACE_DISPONIBLE = False

    def _get_face_app():
        raise RuntimeError(
            "InsightFace no está instalado. "
            "Ejecuta: pip install insightface onnxruntime"
        )


# ─── Helpers de imagen ────────────────────────────────────────────────────────

def bytes_a_bgr(imagen_bytes: bytes) -> np.ndarray:
    """Convierte bytes de imagen (JPEG/PNG) a array BGR de OpenCV."""
    array = np.frombuffer(imagen_bytes, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen")
    return img


def normalizar_l2(vector: np.ndarray) -> np.ndarray:
    """Normalización L2 para comparación por distancia coseno."""
    norma = np.linalg.norm(vector)
    return vector / norma if norma > 0 else vector


# ─── Extracción de embedding ──────────────────────────────────────────────────

def extraer_embedding(imagen_bytes: bytes) -> np.ndarray:
    """
    Recibe los bytes de una imagen y retorna el embedding ArcFace (512-d).
    Lanza ValueError si no se detecta exactamente un rostro.
    """
    img_bgr = bytes_a_bgr(imagen_bytes)
    app = _get_face_app()
    rostros = app.get(img_bgr)

    if len(rostros) == 0:
        raise ValueError("No se detectó ningún rostro en la imagen")
    if len(rostros) > 1:
        raise ValueError(
            f"Se detectaron {len(rostros)} rostros. Envía una imagen con un solo rostro"
        )

    embedding = rostros[0].normed_embedding   # InsightFace ya lo normaliza
    return embedding.astype(np.float32)


def embedding_a_bytes(embedding: np.ndarray) -> bytes:
    """Serializa el embedding a bytes para almacenar en la BD como LargeBinary."""
    return embedding.tobytes()


def bytes_a_embedding(data: bytes) -> np.ndarray:
    """Deserializa bytes de la BD a numpy array float32."""
    return np.frombuffer(data, dtype=np.float32)


# ─── Comparación ──────────────────────────────────────────────────────────────

def similitud_coseno(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Similitud coseno entre dos vectores normalizados.
    Retorna un valor entre -1.0 y 1.0  (1.0 = misma persona).
    """
    vec_a = normalizar_l2(vec_a)
    vec_b = normalizar_l2(vec_b)
    return float(np.dot(vec_a, vec_b))# Placeholder for face utilities (to be implemented later).
