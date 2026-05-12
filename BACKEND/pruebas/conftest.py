"""
conftest.py - Fixtures compartidos para pruebas de V-ESCOM

Provee imágenes de prueba mínimas para los módulos que requieren
analizar imágenes con InsightFace/ArcFace.

Los fixtures generan imágenes JPEG sintéticas mediante PIL/Pillow.
Si Pillow no está instalado, se usan bytes JPEG mínimos.
"""

import io
import pytest

try:
    from PIL import Image as PILImage
    PILLOW_DISPONIBLE = True
except ImportError:
    PILLOW_DISPONIBLE = False


def _crear_jpeg_negro(ancho=200, alto=200) -> bytes:
    """Crea un JPEG negro sólido de dimensiones dadas."""
    if PILLOW_DISPONIBLE:
        img = PILImage.new("RGB", (ancho, alto), color=(0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()
    # Fallback: bytes mínimos que parecen JPEG (sin contenido real)
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100 + b"\xff\xd9"


@pytest.fixture
def imagen_sin_rostro():
    """Imagen JPEG de 200x200 píxeles completamente negra (sin rostros)."""
    return _crear_jpeg_negro(200, 200)


@pytest.fixture
def imagen_un_rostro(tmp_path):
    """
    Ruta de imagen JPEG con un solo rostro.
    Requiere una imagen real para que InsightFace detecte el rostro.
    Por defecto retorna una imagen negra (el test se marcará como skip si
    InsightFace no puede detectar rostros en ella).
    """
    return _crear_jpeg_negro(224, 224)


@pytest.fixture
def imagen_dos_rostros():
    """
    Imagen JPEG con (potencialmente) múltiples rostros.
    Se usa una imagen negra como placeholder; en entorno real
    debe reemplazarse con una foto real de dos personas.
    """
    return _crear_jpeg_negro(400, 200)
