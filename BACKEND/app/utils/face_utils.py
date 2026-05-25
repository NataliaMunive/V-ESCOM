"""
Utilidades de reconocimiento facial usando InsightFace (ArcFace).
"""
from __future__ import annotations

from typing import Optional
import warnings

import cv2
import numpy as np

# InsightFace usa internamente una API de scikit-image marcada como deprecated;
# se filtra solo ese warning para evitar ruido en logs del backend.
warnings.filterwarnings(
    "ignore",
    message=r".*estimate is deprecated.*SimilarityTransform\.from_estimate.*",
    category=FutureWarning,
)

try:
    from insightface.app import FaceAnalysis
    try:
        import onnxruntime as _ort
    except Exception:
        _ort = None

    _face_app: Optional[FaceAnalysis] = None

    def _get_face_app() -> FaceAnalysis:
        """Create (singleton) FaceAnalysis and select ONNX provider if available.

        This avoids warnings when a codepath requests CUDA but the runtime is CPU-only.
        """
        global _face_app
        if _face_app is None:
            providers = None
            try:
                if _ort is not None:
                    available = _ort.get_available_providers()
                    # Prefer GPU providers if available: CUDA (NVIDIA) or DML (DirectML for AMD/Windows)
                    if 'CUDAExecutionProvider' in available:
                        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                    elif 'DmlExecutionProvider' in available or 'DMLExecutionProvider' in available:
                        # onnxruntime-directml exposes DmlExecutionProvider
                        providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                    else:
                        providers = ['CPUExecutionProvider']
            except Exception:
                providers = None

            if providers:
                _face_app = FaceAnalysis(name="buffalo_l", providers=providers)
            else:
                _face_app = FaceAnalysis(name="buffalo_l")

            _face_app.prepare(ctx_id=-1, det_size=(640, 640))
        return _face_app

    INSIGHTFACE_DISPONIBLE = True

except ImportError:
    INSIGHTFACE_DISPONIBLE = False

    def _get_face_app():
        raise RuntimeError(
            "InsightFace no está instalado. "
            "Ejecuta: pip install insightface onnxruntime"
        )


def bytes_a_bgr(imagen_bytes: bytes) -> np.ndarray:
    """Convierte bytes de imagen (JPEG/PNG) a array BGR de OpenCV."""
    array = np.frombuffer(imagen_bytes, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen")
    return img


def _reescalar_para_detecion(img_bgr: np.ndarray, max_lado: int = 1280) -> np.ndarray:
    """Reescala la imagen manteniendo proporción para mejorar el detector cuando viene muy pequeña o muy comprimida."""
    alto, ancho = img_bgr.shape[:2]
    lado_maximo = max(alto, ancho)
    if lado_maximo <= max_lado:
        return img_bgr
    escala = max_lado / float(lado_maximo)
    nuevo_ancho = max(1, int(ancho * escala))
    nuevo_alto = max(1, int(alto * escala))
    return cv2.resize(img_bgr, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)


def normalizar_l2(vector: np.ndarray) -> np.ndarray:
    """Normalización L2 para comparación por distancia coseno."""
    norma = np.linalg.norm(vector)
    return vector / norma if norma > 0 else vector


def extraer_embedding(imagen_bytes: bytes) -> np.ndarray:
    """
    Recibe los bytes de una imagen y retorna el embedding ArcFace (512-d).
    Lanza ValueError si no se detecta exactamente un rostro.
    """
    img_bgr = bytes_a_bgr(imagen_bytes)
    app = _get_face_app()
    rostros = app.get(img_bgr)

    if len(rostros) == 0:
        img_reescalada = _reescalar_para_detecion(img_bgr)
        if img_reescalada is not img_bgr:
            rostros = app.get(img_reescalada)

    if len(rostros) == 0:
        raise ValueError(
            "No se detectó ningún rostro en la imagen. "
            "Prueba con una foto más frontal, sin recortes extremos, con mejor iluminación y en formato JPG/PNG."
        )
    if len(rostros) > 1:
        raise ValueError(
            f"Se detectaron {len(rostros)} rostros. Envía una imagen con un solo rostro"
        )

    embedding = rostros[0].normed_embedding
    return embedding.astype(np.float32)


def similitud_coseno(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Similitud coseno entre dos vectores normalizados.
    Retorna un valor entre -1.0 y 1.0 (1.0 = misma persona).
    """
    vec_a = normalizar_l2(vec_a)
    vec_b = normalizar_l2(vec_b)
    return float(np.dot(vec_a, vec_b))