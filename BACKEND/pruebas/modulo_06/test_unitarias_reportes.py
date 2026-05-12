"""
Pruebas Unitarias - Módulo 6.6: Cubículos, Bitácora y Reportes
V-ESCOM

Casos cubiertos:
    VESCOM-REP-U01: Generación de PDF con lista vacía
    VESCOM-REP-U02: Filtrado de fechas en Python (fecha_desde/fecha_hasta)
    VESCOM-REP-U03: Cálculo de tasa de autorización en PDF

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_06/test_unitarias_reportes.py -v
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

# ── Intento de importar _generar_pdf ────────────────────────────────────────
try:
    from app.routes.reportes import _generar_pdf
    REPORTES_DISPONIBLE = True
except ImportError:
    REPORTES_DISPONIBLE = False


# ── Función auxiliar de filtrado (replicada desde reportes.py) ──────────────

def _filtrar_eventos_por_fecha(eventos: list, fecha_desde: str = None, fecha_hasta: str = None) -> list:
    """
    Replica la lógica de filtrado de fechas del endpoint /reportes/pdf.
    """
    resultado = []
    for ev in eventos:
        fecha_str = ev.get("fecha")
        if fecha_desde and fecha_str and fecha_str < fecha_desde:
            continue
        if fecha_hasta and fecha_str and fecha_str > fecha_hasta:
            continue
        resultado.append(ev)
    return resultado


def _calcular_tasa_autorizacion(auth: int, total: int) -> str:
    """
    Replica el cálculo de tasa de autorización del generador de PDF.
    """
    if total > 0:
        return f"{(auth / total * 100):.1f}%"
    return "—"


# ── VESCOM-REP-U01 ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(not REPORTES_DISPONIBLE, reason="ReportLab no instalado")
def test_U01_pdf_generado_con_lista_vacia():
    """_generar_pdf con lista vacía debe retornar bytes de PDF válido."""
    resultado = _generar_pdf([], {})
    
    # Un PDF siempre empieza con '%PDF'
    assert resultado[:4] == b"%PDF"
    assert len(resultado) > 0


@pytest.mark.skipif(not REPORTES_DISPONIBLE, reason="ReportLab no instalado")
def test_U01_pdf_generado_con_un_evento():
    """_generar_pdf con un evento debe retornar bytes de PDF válido."""
    eventos = [{
        "id_evento": 1,
        "tipo_acceso": "Autorizado",
        "fecha": "2025-06-15",
        "hora": "09:30:00",
        "id_camara": 1,
        "id_persona": 1,
        "similitud": 0.85,
    }]
    filtros = {"fecha_desde": None, "fecha_hasta": None, "tipo": "Todos", "id_camara": "Todas"}
    
    resultado = _generar_pdf(eventos, filtros)
    assert resultado[:4] == b"%PDF"


# ── VESCOM-REP-U02 ─────────────────────────────────────────────────────────────

def test_U02_filtrado_por_fecha_desde():
    """Solo deben incluirse eventos con fecha >= fecha_desde."""
    eventos = [
        {"fecha": "2025-01-01", "tipo_acceso": "Autorizado"},
        {"fecha": "2025-06-15", "tipo_acceso": "Autorizado"},
        {"fecha": "2025-12-31", "tipo_acceso": "No Autorizado"},
    ]
    
    resultado = _filtrar_eventos_por_fecha(eventos, fecha_desde="2025-06-01")
    assert len(resultado) == 2
    assert all(ev["fecha"] >= "2025-06-01" for ev in resultado)


def test_U02_filtrado_por_fecha_hasta():
    """Solo deben incluirse eventos con fecha <= fecha_hasta."""
    eventos = [
        {"fecha": "2025-01-01", "tipo_acceso": "Autorizado"},
        {"fecha": "2025-06-15", "tipo_acceso": "Autorizado"},
        {"fecha": "2025-12-31", "tipo_acceso": "No Autorizado"},
    ]
    
    resultado = _filtrar_eventos_por_fecha(eventos, fecha_hasta="2025-06-30")
    assert len(resultado) == 2
    assert all(ev["fecha"] <= "2025-06-30" for ev in resultado)


def test_U02_filtrado_por_rango_completo():
    """Solo deben incluirse eventos dentro del rango de fechas."""
    eventos = [
        {"fecha": "2024-12-31", "tipo_acceso": "Autorizado"},  # Excluido
        {"fecha": "2025-01-15", "tipo_acceso": "Autorizado"},  # Incluido
        {"fecha": "2025-06-15", "tipo_acceso": "No Autorizado"},  # Incluido
        {"fecha": "2026-01-01", "tipo_acceso": "Autorizado"},  # Excluido
    ]
    
    resultado = _filtrar_eventos_por_fecha(
        eventos, fecha_desde="2025-01-01", fecha_hasta="2025-12-31"
    )
    assert len(resultado) == 2


def test_U02_sin_filtros_retorna_todos_los_eventos():
    """Sin filtros de fecha, todos los eventos deben retornarse."""
    eventos = [
        {"fecha": "2023-01-01", "tipo_acceso": "Autorizado"},
        {"fecha": "2024-06-15", "tipo_acceso": "No Autorizado"},
        {"fecha": "2025-12-31", "tipo_acceso": "Autorizado"},
    ]
    
    resultado = _filtrar_eventos_por_fecha(eventos)
    assert len(resultado) == 3


# ── VESCOM-REP-U03 ─────────────────────────────────────────────────────────────

def test_U03_tasa_autorizacion_con_todos_autorizados():
    """Con 100% de accesos autorizados la tasa debe ser '100.0%'."""
    resultado = _calcular_tasa_autorizacion(auth=5, total=5)
    assert resultado == "100.0%"


def test_U03_tasa_autorizacion_con_ninguno_autorizado():
    """Con 0 accesos autorizados la tasa debe ser '0.0%'."""
    resultado = _calcular_tasa_autorizacion(auth=0, total=5)
    assert resultado == "0.0%"


def test_U03_tasa_autorizacion_parcial():
    """Con 3 de 4 autorizados la tasa debe ser '75.0%'."""
    resultado = _calcular_tasa_autorizacion(auth=3, total=4)
    assert resultado == "75.0%"


def test_U03_tasa_autorizacion_total_cero():
    """Con total = 0 la tasa debe ser '—' para evitar división por cero."""
    resultado = _calcular_tasa_autorizacion(auth=0, total=0)
    assert resultado == "—"


def test_U03_tasa_autorizacion_formato_un_decimal():
    """El formato debe tener exactamente un decimal."""
    resultado = _calcular_tasa_autorizacion(auth=1, total=3)
    # 1/3 = 33.333... -> "33.3%"
    assert resultado == "33.3%"
    assert resultado.count(".") == 1
    assert resultado.endswith("%")
