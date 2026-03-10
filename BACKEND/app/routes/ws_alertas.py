"""
Router de Tiempo Real (WebSockets) - V-ESCOM

Gestiona las conexiones persistentes para el envío de notificaciones push
hacia el cliente administrativo. Implementa seguridad por Token JWT vía Query.

manejo de errores:
- Si el token JWT no se proporciona, es inválido o ha expirado, se cierra la conexión con un código de violación de política (1008) y un mensaje descriptivo.
- Si el administrador asociado al token no existe o no está activo, se cierra la conexión con un código de violación de política (1008) y un mensaje de acceso denegado.
- Se implementa un mecanismo de heartbeat (ping/pong) para mantener la conexión viva y detectar desconexiones de manera eficiente.
- En caso de desconexión inesperada o errores durante la comunicación, se asegura la limpieza de recursos y la desconexión del cliente para evitar hilos huérfanos.

"""

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.security import decode_access_token
from app.models.administrador import Administrador
from app.services.websocket_manager import alertas_ws_manager

router = APIRouter(tags=["WebSocket Alertas"])


@router.websocket("/ws/alertas")
async def ws_alertas(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Endpoint de WebSocket para alertas en tiempo real.
    
    Flujo:
    1. Valida el token JWT enviado en la URL.
    2. Verifica que el administrador esté activo en la DB.
    3. Registra la conexión en el AlertasWSManager.
    4. Mantiene un bucle de escucha para mantener la conexión viva (Heartbeat).
    """
    
    # ─── VALIDACIÓN DE SEGURIDAD ───
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token requerido")
        return

    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalido")
        return

    admin_id = payload.get("sub")
    if admin_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalido")
        return

    # Verificamos integridad del usuario contra la base de datos
    admin = (
        db.query(Administrador)
        .filter(Administrador.id_admin == int(admin_id), Administrador.activo.is_(True))
        .first()
    )
    if admin is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Acceso denegado")
        return

    # ─── GESTIÓN DE LA CONEXIÓN ───
    await alertas_ws_manager.connect(websocket)
    
    # Confirmación de conexión exitosa al cliente
    await websocket.send_json({"type": "conexion", "message": "Canal de alertas activo"})

    try:
        while True:
            # Esperamos mensajes del cliente (usualmente para Keep-Alive)
            mensaje = await websocket.receive_text()
            if mensaje.lower() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        # Limpieza cuando el cliente cierra el navegador o pierde internet
        alertas_ws_manager.disconnect(websocket)
    except Exception:
        # Prevención de hilos huérfanos ante errores inesperados
        alertas_ws_manager.disconnect(websocket)