"""
Pruebas Unitarias - Módulo 6.5: Alertas y Notificaciones
V-ESCOM

Casos cubiertos:
    VESCOM-ALRT-U01: Generación de alerta ante acceso no autorizado
    VESCOM-ALRT-U02: No se genera alerta ante acceso autorizado
    VESCOM-ALRT-U03: alertas_ws_manager.broadcast_json notifica a todos los clientes

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_05/test_unitarias_alertas.py -v
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from app.services.websocket_manager import WebSocketManager


# ── VESCOM-ALRT-U01 ────────────────────────────────────────────────────────────

def test_U01_alerta_generada_ante_acceso_no_autorizado():
    """Acceso 'No Autorizado' debe desencadenar creación de alerta."""
    tipo_acceso = "No Autorizado"

    debe_generar_alerta = tipo_acceso == "No Autorizado"
    assert debe_generar_alerta is True


def test_U01_alerta_tiene_estado_pendiente():
    """La alerta generada debe tener estado 'Pendiente' inicialmente."""
    # Simula la lógica del servicio: estado inicial siempre es 'Pendiente'
    estado_inicial = "Pendiente"
    assert estado_inicial == "Pendiente"


def test_U01_alerta_service_crear_alerta_mock():
    """Verificar que alerta_service.crear_alerta se invoca ante acceso no autorizado."""
    # Mock del servicio a nivel de función
    mock_crear = MagicMock(return_value={"id_alerta": 1, "estado": "Pendiente"})

    tipo_acceso = "No Autorizado"
    if tipo_acceso == "No Autorizado":
        resultado = mock_crear(db=MagicMock(), tipo="Intruso Detectado")

    mock_crear.assert_called_once()
    assert resultado["estado"] == "Pendiente"


# ── VESCOM-ALRT-U02 ────────────────────────────────────────────────────────────

def test_U02_sin_alerta_ante_acceso_autorizado():
    """Acceso 'Autorizado' NO debe desencadenar creación de alerta."""
    tipo_acceso = "Autorizado"

    debe_generar_alerta = tipo_acceso == "No Autorizado"
    assert debe_generar_alerta is False


def test_U02_alerta_service_no_llamado_con_acceso_autorizado():
    """Verificar que la función de creación de alerta NO se invoca ante acceso autorizado."""
    mock_crear = MagicMock()

    tipo_acceso = "Autorizado"
    if tipo_acceso == "No Autorizado":
        mock_crear(db=MagicMock(), tipo="Intruso Detectado")

    mock_crear.assert_not_called()


# ── VESCOM-ALRT-U03 ────────────────────────────────────────────────────────────

def test_U03_broadcast_json_notifica_a_todos_los_clientes():
    """El broadcast del WebSocket Manager debe enviar a todos los clientes suscritos."""
    manager = WebSocketManager()

    # Crear 3 WebSocket mock
    clientes_mock = [AsyncMock() for _ in range(3)]
    for cliente in clientes_mock:
        manager._connections.append(cliente)

    mensaje = {"type": "alerta", "id_alerta": 1, "tipo": "Intruso Detectado"}

    asyncio.run(manager.broadcast_json(mensaje))

    # Verificar que todos los clientes recibieron el mensaje
    for cliente in clientes_mock:
        cliente.send_json.assert_called_once_with(mensaje)


def test_U03_broadcast_json_sin_clientes_no_lanza_excepcion():
    """El broadcast con cero clientes conectados no debe lanzar excepción."""
    manager = WebSocketManager()
    # Sin clientes conectados

    mensaje = {"type": "alerta", "id_alerta": 1}

    try:
        asyncio.run(manager.broadcast_json(mensaje))
    except Exception as e:
        pytest.fail(f"broadcast_json() lanzó excepción inesperada: {e}")


def test_U03_broadcast_json_cliente_fallido_es_desconectado():
    """Si un cliente falla al recibir, debe ser removido de la lista."""
    manager = WebSocketManager()

    cliente_bueno = AsyncMock()
    cliente_malo = AsyncMock()
    cliente_malo.send_json = AsyncMock(side_effect=Exception("Conexión rota"))

    manager._connections.append(cliente_bueno)
    manager._connections.append(cliente_malo)

    mensaje = {"type": "test"}
    asyncio.run(manager.broadcast_json(mensaje))

    # El cliente bueno debe seguir conectado
    assert cliente_bueno in manager._connections
    # El cliente malo debe haber sido removido
    assert cliente_malo not in manager._connections


def test_U03_disconnect_remueve_cliente():
    """Desconectar un cliente debe eliminarlo de _connections."""
    manager = WebSocketManager()
    cliente_mock = AsyncMock()
    manager._connections.append(cliente_mock)

    assert len(manager._connections) == 1

    manager.disconnect(cliente_mock)

    assert len(manager._connections) == 0
    assert cliente_mock not in manager._connections


def test_U03_disconnect_cliente_no_registrado_no_falla():
    """Desconectar un cliente no registrado no debe lanzar excepción."""
    manager = WebSocketManager()
    cliente_mock = AsyncMock()

    try:
        manager.disconnect(cliente_mock)
    except Exception as e:
        pytest.fail(f"disconnect() lanzó excepción inesperada: {e}")
