"""""
Servicio para gestionar notificaciones relacionadas con eventos de seguridad

Funciones principales:
- notificar_intrusion: Crea una alerta y envía notificaciones SMS a los administradores activos con telefono registrado.

Implementacion:
- Se utiliza Twilio para el envio de SMS, con configuracion a traves de variables de entorno.
- Se registra cada notificacion en la base de datos, incluyendo su estado (enviado, no configurado, error).
- Si no hay destinatarios disponibles, se registra una notificación con estado Sin destinatario y no se intenta enviar SMS.
"""
from __future__ import annotations

import os
from typing import List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.administrador import Administrador
from app.models.alerta import Alerta
from app.models.camara import Camara
from app.models.evento import EventoAcceso
from app.models.notificacion import Notificacion
from app.models.profesor import Profesor
from app.utils.phone_utils import normalizar_telefono_mx

try:
    from twilio.rest import Client
except ImportError:
    Client = None

# ─── Funciones Auxiliares ────────────────────────────────────────────────────────
# obtenemos destinatarios activos con telefono registrado para intrusiones
def _obtener_destinatarios_intrusion(db: Session) -> List[Tuple[str, str]]:
    admins = (
        db.query(Administrador)
        .filter(Administrador.activo.is_(True))
        .filter(Administrador.telefono.isnot(None))
        .all()
    )

    # Normalizamos teléfonos y preparamos lista de destinatarios (nombre, telefono)
    destinatarios: List[Tuple[str, str]] = []
    for admin in admins:
        telefono = normalizar_telefono_mx(admin.telefono)
        if telefono:
            nombre = f"{admin.nombre} {admin.apellidos}".strip()
            destinatarios.append((nombre, telefono))
    return destinatarios

# obtenemos profesores activos del cubiculo con telefono valido
def _obtener_destinatarios_cubiculo(db: Session, id_cubiculo: int) -> List[Tuple[str, str]]:
    """Obtiene profesores activos del cubiculo con telefono valido."""
    profesores = (
        db.query(Profesor)
        .filter(Profesor.id_cubiculo == id_cubiculo)
        .filter(Profesor.activo.is_(True))
        .filter(Profesor.telefono.isnot(None))
        .all()
    )

    # Normalizamos teléfonos y preparamos lista de destinatarios (nombre, telefono)
    destinatarios: List[Tuple[str, str]] = []
    for profesor in profesores:
        telefono = normalizar_telefono_mx(profesor.telefono)
        if telefono:
            destinatarios.append((f"Prof. {profesor.nombre}".strip(), telefono))
    return destinatarios

# obtenemos id_cubiculo del evento a partir de la camara 
def _obtener_id_cubiculo_evento(db: Session, evento: EventoAcceso) -> int | None:
    camara = db.query(Camara).filter(Camara.id_camara == evento.id_camara).first()
    if camara is None:
        return None
    return camara.id_cubiculo

# crear cliente de Twilio si las variables de entorno estan configuradas, sino retorna None
def _crear_cliente_twilio():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token or Client is None:
        return None

    return Client(account_sid, auth_token)

# notificar_intrusion: Crea una alerta y envía notificaciones SMS a los administradores activos con telefono registrado.
def notificar_intrusion(db: Session, evento: EventoAcceso) -> None:
    alerta = Alerta(
        id_evento=evento.id_evento,
        tipo_alerta="Intrusion",
        estado="Pendiente",
    )
    db.add(alerta)
    db.flush()
    # Obtener destinatarios: administradores activos con telefono + profesores del cubiculo
    admins = _obtener_destinatarios_intrusion(db)
    id_cubiculo = _obtener_id_cubiculo_evento(db, evento)
    profesores = _obtener_destinatarios_cubiculo(db, id_cubiculo) if id_cubiculo is not None else []
    # Unir y eliminar duplicados (mismo telefono) entre admins y profesores
    destinatarios: List[Tuple[str, str]] = []
    vistos: Set[str] = set()
    # Primero los admins, luego los profesores (si hay solapamiento, se prioriza admin)
    for nombre, telefono in admins + profesores:
        if telefono not in vistos:
            destinatarios.append((nombre, telefono))
            vistos.add(telefono)
    # Si no hay destinatarios, registrar notificación sin destinatario y salir
    if not destinatarios:
        db.add(
            Notificacion(
                id_alerta=alerta.id_alerta,
                destinatario="Sin destinatario",
                telefono=None,
                medio="SMS",
                estado="Sin destinatario",
            )
        )
        db.commit()
        return
    # Enviar SMS a cada destinatario y registrar resultado
    twilio_client = _crear_cliente_twilio()
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

    cuerpo = (
    f"[V-ESCOM] INTRUSIÓN en C- {id_cubiculo if id_cubiculo else '??'}. "
    f"Evento #{evento.id_evento} | Cam:{evento.id_camara} | "
    f"{evento.fecha} {evento.hora}"
    )

    enviados = 0
    
    for nombre, telefono in destinatarios:
        estado = "Pendiente"
        if twilio_client is None or not messaging_service_sid:
            estado = "No configurado"
        else:
            try:
                twilio_client.messages.create(
                    messaging_service_sid=messaging_service_sid,
                    body=cuerpo,
                    to=telefono,
                )
                estado = "Enviado"
                enviados += 1
            except Exception:
                estado = "Error"

        db.add(
            Notificacion(
                id_alerta=alerta.id_alerta,
                destinatario=nombre,
                telefono=telefono,
                medio="SMS",
                estado=estado,
            )
        )

    alerta.estado = "Notificada" if enviados > 0 else "Pendiente"
    db.commit()
