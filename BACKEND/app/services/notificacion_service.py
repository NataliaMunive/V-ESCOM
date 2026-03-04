from __future__ import annotations

import os
import re
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models.administrador import Administrador
from app.models.alerta import Alerta
from app.models.evento import EventoAcceso
from app.models.notificacion import Notificacion

try:
    from twilio.rest import Client
except ImportError:
    Client = None


def _normalizar_telefono(telefono: str | None) -> str | None:
    if not telefono:
        return None
    telefono = telefono.strip()
    if not telefono:
        return None

    # Mantener solo dígitos para mapear formatos locales a E.164
    solo_digitos = re.sub(r"\D", "", telefono)
    if not solo_digitos:
        return None

    # México local (10 dígitos) -> +52XXXXXXXXXX
    if len(solo_digitos) == 10:
        return f"+52{solo_digitos}"

    # México con lada país sin '+' -> +52XXXXXXXXXX
    if len(solo_digitos) == 12 and solo_digitos.startswith("52"):
        return f"+{solo_digitos}"

    # Formato histórico móvil México +521XXXXXXXXXX -> +52XXXXXXXXXX
    if len(solo_digitos) == 13 and solo_digitos.startswith("521"):
        return f"+52{solo_digitos[3:]}"

    # Si ya viene internacional, validar estructura mínima
    telefono_e164 = f"+{solo_digitos}"
    if re.fullmatch(r"\+[1-9]\d{7,14}", telefono_e164):
        return telefono_e164

    return None


def _obtener_destinatarios_intrusion(db: Session) -> List[Tuple[str, str]]:
    admins = (
        db.query(Administrador)
        .filter(Administrador.activo.is_(True))
        .filter(Administrador.telefono.isnot(None))
        .all()
    )

    destinatarios: List[Tuple[str, str]] = []
    for admin in admins:
        telefono = _normalizar_telefono(admin.telefono)
        if telefono:
            nombre = f"{admin.nombre} {admin.apellidos}".strip()
            destinatarios.append((nombre, telefono))
    return destinatarios


def _crear_cliente_twilio():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token or Client is None:
        return None

    return Client(account_sid, auth_token)


def notificar_intrusion(db: Session, evento: EventoAcceso) -> None:
    alerta = Alerta(
        id_evento=evento.id_evento,
        tipo_alerta="Intrusion",
        estado="Pendiente",
    )
    db.add(alerta)
    db.flush()

    destinatarios = _obtener_destinatarios_intrusion(db)
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

    twilio_client = _crear_cliente_twilio()
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

    cuerpo = (
        f"[V-ESCOM] Alerta de intrusión. Evento #{evento.id_evento}, "
        f"camara={evento.id_camara}, fecha={evento.fecha}, hora={evento.hora}."
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
