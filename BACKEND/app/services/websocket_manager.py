"""
Gestor de Conexiones en Tiempo Real - V-ESCOM

Implementa un patrón de difusión (Broadcast) para enviar notificaciones push
a múltiples clientes conectados simultáneamente sin bloquear el hilo principal.
"""

from __future__ import annotations
from fastapi import WebSocket


class WebSocketManager:
    """
    Administra el ciclo de vida de las conexiones WebSocket.
    
    Permite el registro de nuevos clientes y garantiza que los mensajes se envíen solo a conexiones que sigan activas, limpiando automáticamente aquellas que hayan fallado.
    """
    def __init__(self) -> None:
        # Lista privada de sockets activos (administradores logueados)
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Acepta el apretón de manos inicial y registra al cliente."""
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remueve la conexión de la lista de difusión."""
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        """
        Envía un objeto JSON a todos los administradores conectados.
        
        Implementa una estrategia de 'Fail-Safe': si un envío falla (por ejemplo, si el cliente cerró su pestaña bruscamente), se desconecta automáticamente del registro para mantener la lista depurada.
        """
        # Creamos una copia de la lista para iterar de forma segura
        conexiones_activas = list(self._connections)
        for websocket in conexiones_activas:
            try:
                await websocket.send_json(payload)
            except Exception:
                # Si el socket está roto, lo removemos para no desperdiciar recursos
                self.disconnect(websocket)

# Instancia global para ser utilizada en routers y servicios
alertas_ws_manager = WebSocketManager()