"""
Pruebas Unitarias - Módulo 6.3: Cámaras y Streaming RTSP
V-ESCOM

Casos cubiertos:
    VESCOM-CAM-U01: Parseo de URL RTSP vs. índice de webcam
    VESCOM-CAM-U02: Lectura de bytes por FrameUpload
    VESCOM-CAM-U03: detener_stream_activo con cámara no activa
    VESCOM-CAM-U04: detener_stream_activo con cámara activa (mock)

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_03/test_unitarias_camaras.py -v
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.routes.stream import FrameUpload, _tareas_activas, detener_stream_activo
from app.services.rtsp_manager import construir_rtsp_url, resolver_rtsp_url_camara


# ── VESCOM-CAM-U01 ─────────────────────────────────────────────────────────────

def test_U01_parseo_url_cero_a_entero():
    """La cadena '0' debe convertirse al entero 0 para webcam local."""
    url_stream = "0"
    fuente = int(url_stream) if url_stream.isdigit() else url_stream
    assert fuente == 0
    assert isinstance(fuente, int)


def test_U01_parseo_url_rtsp_permanece_cadena():
    """Una URL RTSP no debe convertirse a entero."""
    url_stream = "rtsp://192.168.1.100:554/stream"
    fuente = int(url_stream) if url_stream.isdigit() else url_stream
    assert fuente == url_stream
    assert isinstance(fuente, str)


def test_U01_parseo_ip_local_permanece_cadena():
    """Una IP con puntos no debe convertirse a entero."""
    url_stream = "192.168.1.100"
    fuente = int(url_stream) if url_stream.isdigit() else url_stream
    assert fuente == url_stream
    assert isinstance(fuente, str)


def test_U01_construir_rtsp_url_escapa_credenciales_especiales():
    """Los caracteres reservados en usuario y contraseña deben codificarse."""
    url = construir_rtsp_url(
        "192.168.1.50",
        user="admin@vescom",
        pwd="Vescoma023!",
        stream="stream1",
    )
    assert url == "rtsp://admin%40vescom:Vescoma023%21@192.168.1.50:554/stream1"


def test_U01_resolver_rtsp_url_prioriza_url_especifica_por_camara(monkeypatch):
    """Si existe RTSP_URL_<id>, debe ganar sobre usuario, contraseña y stream."""
    camara = SimpleNamespace(direccion_ip="192.168.1.60")
    monkeypatch.setenv("RTSP_URL_4", "rtsp://admin:pass@192.168.1.60:554/stream2")
    monkeypatch.setenv("RTSP_USER", "otro")
    monkeypatch.setenv("RTSP_PASS", "otra")
    monkeypatch.setenv("RTSP_STREAM", "stream1")

    url = resolver_rtsp_url_camara(camara, 4, user="manual", pwd="manual", stream="stream1")

    assert url == "rtsp://admin:pass@192.168.1.60:554/stream2"


def test_U01_resolver_rtsp_url_usa_credenciales_por_camara(monkeypatch):
    """Las credenciales específicas de la cámara deben prevalecer sobre las globales."""
    camara = SimpleNamespace(direccion_ip="192.168.1.61")
    monkeypatch.delenv("RTSP_URL_4", raising=False)
    monkeypatch.setenv("RTSP_USER_4", "camara4")
    monkeypatch.setenv("RTSP_PASS_4", "clave:camara@4")
    monkeypatch.setenv("RTSP_STREAM_4", "stream1")
    monkeypatch.setenv("RTSP_USER", "global")
    monkeypatch.setenv("RTSP_PASS", "global")
    monkeypatch.setenv("RTSP_STREAM", "stream2")

    url = resolver_rtsp_url_camara(camara, 4)

    assert url == "rtsp://camara4:clave%3Acamara%404@192.168.1.61:554/stream1"


def test_U01_resolver_rtsp_url_respeta_url_directa_en_bd(monkeypatch):
    """Si la cámara ya guarda una URL directa, no debe reconstruirse."""
    camara = SimpleNamespace(direccion_ip="rtsp://usuario:pass@192.168.1.70:554/stream2")
    monkeypatch.setenv("RTSP_URL_4", "rtsp://admin:pass@192.168.1.60:554/stream2")

    url = resolver_rtsp_url_camara(camara, 4, user="otro", pwd="otra", stream="stream1")

    assert url == "rtsp://usuario:pass@192.168.1.70:554/stream2"


# ── VESCOM-CAM-U02 ─────────────────────────────────────────────────────────────

def test_U02_frame_upload_retorna_bytes_originales():
    """FrameUpload.read() debe retornar exactamente los bytes originales."""
    bytes_prueba = b"frame de prueba en JPEG"
    frame = FrameUpload(bytes_prueba)
    
    # Ejecutar coroutine en event loop
    resultado = asyncio.run(frame.read())
    assert resultado == bytes_prueba


def test_U02_frame_upload_nombre_es_frame_jpg():
    """FrameUpload.filename debe ser 'frame.jpg'."""
    frame = FrameUpload(b"datos")
    assert frame.filename == "frame.jpg"


def test_U02_frame_upload_bytes_vacios():
    """FrameUpload debe manejar bytes vacíos sin error."""
    frame = FrameUpload(b"")
    resultado = asyncio.run(frame.read())
    assert resultado == b""


# ── VESCOM-CAM-U03 ─────────────────────────────────────────────────────────────

def test_U03_detener_stream_activo_camara_no_monitoreada():
    """detener_stream_activo con ID no registrado debe retornar False sin excepción."""
    # Asegurar que la cámara 9999 no está en tareas activas
    _tareas_activas.pop(9999, None)
    
    resultado = detener_stream_activo(9999)
    assert resultado is False


def test_U03_detener_stream_activo_id_negativo():
    """ID negativo no registrado debe retornar False."""
    resultado = detener_stream_activo(-1)
    assert resultado is False


# ── VESCOM-CAM-U04 ─────────────────────────────────────────────────────────────

def test_U04_detener_stream_activo_con_tarea_mock():
    """detener_stream_activo con tarea activa debe retornar True y cancelar la tarea."""
    tarea_mock = MagicMock()
    tarea_mock.cancel = MagicMock()
    
    id_camara_prueba = 777
    _tareas_activas[id_camara_prueba] = tarea_mock
    
    try:
        resultado = detener_stream_activo(id_camara_prueba)
        assert resultado is True
        tarea_mock.cancel.assert_called_once()
        assert id_camara_prueba not in _tareas_activas
    finally:
        # Limpieza defensiva
        _tareas_activas.pop(id_camara_prueba, None)


def test_U04_detener_stream_activo_remueve_de_diccionario():
    """La cámara debe eliminarse de _tareas_activas tras detenerla."""
    tarea_mock = MagicMock()
    id_camara_prueba = 888
    _tareas_activas[id_camara_prueba] = tarea_mock
    
    try:
        detener_stream_activo(id_camara_prueba)
        assert id_camara_prueba not in _tareas_activas
    finally:
        _tareas_activas.pop(id_camara_prueba, None)
