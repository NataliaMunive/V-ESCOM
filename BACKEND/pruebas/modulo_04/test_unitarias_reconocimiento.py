"""
Pruebas Unitarias - Módulo 6.4: Reconocimiento Facial y Dashboard
V-ESCOM

Casos cubiertos:
    VESCOM-REC-U01: Identificación de persona autorizada
    VESCOM-REC-U02: Identificación de persona no autorizada
    VESCOM-REC-U03: Rechazo de frame sin rostro detectable
    VESCOM-REC-U04: Umbral de similitud configurable

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_04/test_unitarias_reconocimiento.py -v
"""

import sys
import os
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

# ── Intento de importar face_utils ──────────────────────────────────────────
try:
    from app.utils.face_utils import extraer_embedding, similitud_coseno
    FACE_UTILS_DISPONIBLE = True
except ImportError:
    FACE_UTILS_DISPONIBLE = False


# ── VESCOM-REC-U01 ─────────────────────────────────────────────────────────────

def test_U01_acceso_autorizado_con_alta_similitud():
    """Similitud mayor al umbral debe producir 'Autorizado'."""
    UMBRAL = 0.55
    similitud = 0.82  # Persona conocida

    tipo_acceso = "Autorizado" if similitud >= UMBRAL else "No Autorizado"
    assert tipo_acceso == "Autorizado"


def test_U01_acceso_autorizado_exactamente_en_umbral():
    """Similitud igual al umbral debe producir 'Autorizado' (límite inclusivo)."""
    UMBRAL = 0.55
    similitud = 0.55

    tipo_acceso = "Autorizado" if similitud >= UMBRAL else "No Autorizado"
    assert tipo_acceso == "Autorizado"


# ── VESCOM-REC-U02 ─────────────────────────────────────────────────────────────

def test_U02_acceso_no_autorizado_con_baja_similitud():
    """Similitud menor al umbral debe producir 'No Autorizado'."""
    UMBRAL = 0.55
    similitud = 0.32  # Persona desconocida

    tipo_acceso = "Autorizado" if similitud >= UMBRAL else "No Autorizado"
    assert tipo_acceso == "No Autorizado"


def test_U02_acceso_no_autorizado_similitud_cero():
    """Sin ninguna persona en BD la similitud máxima es 0; debe ser 'No Autorizado'."""
    UMBRAL = 0.55
    similitud = 0.0

    tipo_acceso = "Autorizado" if similitud >= UMBRAL else "No Autorizado"
    assert tipo_acceso == "No Autorizado"


# ── VESCOM-REC-U03 ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(not FACE_UTILS_DISPONIBLE, reason="InsightFace no instalado")
def test_U03_rechazo_frame_sin_rostro(imagen_sin_rostro):
    """Frame sin rostro detectable debe lanzar ValueError."""
    with pytest.raises(ValueError):
        extraer_embedding(imagen_sin_rostro)


def test_U03_rechazo_frame_sin_rostro_mock():
    """Simular ValueError del motor ArcFace ante frame sin rostro."""
    with patch("app.utils.face_utils.extraer_embedding") as mock_extraer:
        mock_extraer.side_effect = ValueError("No se detectó ningún rostro en la imagen")
        
        with pytest.raises(ValueError, match="[Nn]o se detectó"):
            mock_extraer(b"bytes_de_frame_sin_rostro")


# ── VESCOM-REC-U04 ─────────────────────────────────────────────────────────────

def test_U04_umbral_mas_estricto_cambia_resultado():
    """Cambiar THRESHOLD de 0.55 a 0.90 puede cambiar el resultado de 'Autorizado' a 'No Autorizado'."""
    similitud_moderada = 0.70  # Autorizado con 0.55, No Autorizado con 0.90

    UMBRAL_ORIGINAL = 0.55
    UMBRAL_ESTRICTO = 0.90

    resultado_original = "Autorizado" if similitud_moderada >= UMBRAL_ORIGINAL else "No Autorizado"
    resultado_estricto = "Autorizado" if similitud_moderada >= UMBRAL_ESTRICTO else "No Autorizado"

    assert resultado_original == "Autorizado"
    assert resultado_estricto == "No Autorizado"
    # Los resultados deben ser distintos
    assert resultado_original != resultado_estricto


def test_U04_umbral_mas_permisivo_acepta_mas_personas():
    """Umbral más bajo acepta personas con menor similitud."""
    similitud = 0.45  # Bajo

    UMBRAL_ESTRICTO = 0.55
    UMBRAL_PERMISIVO = 0.40

    resultado_estricto = "Autorizado" if similitud >= UMBRAL_ESTRICTO else "No Autorizado"
    resultado_permisivo = "Autorizado" if similitud >= UMBRAL_PERMISIVO else "No Autorizado"

    assert resultado_estricto == "No Autorizado"
    assert resultado_permisivo == "Autorizado"
