# app/services/notificacion_service.py
import os
import requests # O la librería que uses para Telegram

def enviar_alerta_telegram(mensaje: str, ruta_imagen: str = None, chat_id: str = None):
    """
    Envía un mensaje a Telegram. 
    Si chat_id es proporcionado, se envía a ese usuario.
    Si no, usa el ID por defecto del .env.
    """
    # Usamos el chat_id que recibimos, o si es None, el del .env
    target_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not target_chat_id or not token:
        print("Error: Falta configurar TELEGRAM_TOKEN o el chat_id es inválido")
        return False

    try:
        # Si hay imagen, usamos sendPhoto (mejor visualización)
        if ruta_imagen:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(ruta_imagen, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": target_chat_id, "caption": mensaje}
                resp = requests.post(url, data=data, files=files, timeout=10)
            return resp.status_code == 200

        # Si no hay imagen, mensaje de texto simple
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": target_chat_id, "text": mensaje}
        resp = requests.post(url, json=payload, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error en envío Telegram: {e}")
        return False


def notificar_intrusion(db, evento, enviar_sms: bool = False):
    """
    Notifica una intrusión a administradores y personas autorizadas que tengan
    `telegram_chat_id` definido. Crea una entrada en la tabla `alertas` y devuelve
    un resumen apto para enviarse por WebSocket.
    """
    from app.models.alerta import Alerta
    from app.models.evento import EventoAcceso
    from app.models.administrador import Administrador
    from app.models.notificacion import Notificacion
    from app.models.persona_autorizada import PersonaAutorizada

    # Anti-spam: cooldown por cámara (segundos)
    from datetime import datetime, timedelta
    COOLDOWN = int(os.getenv("TELEGRAM_COOLDOWN_SECONDS", "300"))

    # Intentamos obtener la cámara para conocer su `id_cubiculo`
    from app.models.camara import Camara
    camara = None
    cam_id = getattr(evento, "id_camara", None)
    if cam_id is not None:
        camara = db.query(Camara).filter(Camara.id_camara == cam_id).first()
    id_cubiculo = camara.id_cubiculo if camara else None

    # Comprobar la última alerta NOTIFICADA para esta cámara
    ultimo_notificado = (
        db.query(Alerta)
        .join(EventoAcceso, EventoAcceso.id_evento == Alerta.id_evento)
        .filter(EventoAcceso.id_camara == cam_id, Alerta.estado == "Notificada")
        .order_by(Alerta.id_alerta.desc())
        .first()
    )

    ahora = datetime.utcnow()
    bajo_cooldown = False
    if ultimo_notificado:
        try:
            fecha = getattr(ultimo_notificado, "fecha", None)
            hora = getattr(ultimo_notificado, "hora", None)
            if fecha and hora:
                dt_last = datetime.combine(fecha, hora)
            else:
                dt_last = None
        except Exception:
            dt_last = None

        if dt_last and (ahora - dt_last).total_seconds() < COOLDOWN:
            bajo_cooldown = True

    # Crear alertas en BD (siempre registramos el evento)
    alerta = Alerta(id_evento=evento.id_evento, tipo_alerta="Intrusion", estado="Pendiente")
    db.add(alerta)
    db.commit()
    db.refresh(alerta)

    mensaje = f"🚨 Alerta de intrusión (evento #{evento.id_evento}) - Cámara: {cam_id or 'Desconocida'}"
    ruta = getattr(evento, "ruta_imagen_captura", None)

    # Si estamos en cooldown, no enviar notificaciones para evitar spam
    if bajo_cooldown:
        return {
            "id_alerta": alerta.id_alerta,
            "id_evento": evento.id_evento,
            "estado": "Pendiente",
            "motivo": f"Cooldown activo ({COOLDOWN}s) para cámara {cam_id}",
        }

    notificados = 0
    errores = 0
    notificacion_registros = []

    # Recolectar destinatarios: administradores (global) y personas autorizadas del mismo cubículo
    admins = db.query(Administrador).filter(Administrador.telegram_chat_id.isnot(None)).all()
    if id_cubiculo is not None:
        personas = (
            db.query(PersonaAutorizada)
            .filter(PersonaAutorizada.telegram_chat_id.isnot(None))
            .filter(PersonaAutorizada.id_cubiculo == id_cubiculo)
            .all()
        )
    else:
        personas = []

    destinatarios = []
    for a in admins:
        if a.telegram_chat_id:
            destinatarios.append((a.telegram_chat_id, f"Admin: {a.nombre} {a.apellidos}"))
    for p in personas:
        if p.telegram_chat_id:
            destinatarios.append((p.telegram_chat_id, f"Persona autorizada: {p.nombre} {p.apellidos}"))

    for chat_id, label in destinatarios:
        try:
            ok = enviar_alerta_telegram(mensaje=f"{mensaje}\n{label}", ruta_imagen=ruta, chat_id=chat_id)
            if ok:
                notificados += 1
                notificacion_registros.append(Notificacion(
                    id_alerta=alerta.id_alerta,
                    destinatario=label,
                    medio="Telegram",
                    estado="Enviado",
                    telefono=str(chat_id),
                ))
            else:
                errores += 1
                notificacion_registros.append(Notificacion(
                    id_alerta=alerta.id_alerta,
                    destinatario=label,
                    medio="Telegram",
                    estado="Error",
                    telefono=str(chat_id),
                ))
        except Exception:
            errores += 1
            notificacion_registros.append(Notificacion(
                id_alerta=alerta.id_alerta,
                destinatario=label,
                medio="Telegram",
                estado="Error",
                telefono=str(chat_id),
            ))

    if not destinatarios:
        notificacion_registros.append(Notificacion(
            id_alerta=alerta.id_alerta,
            destinatario=None,
            medio="Telegram",
            estado="Sin destinatario",
            telefono=None,
        ))

    for notificacion in notificacion_registros:
        db.add(notificacion)

    # Actualizar estado de la alerta según resultados
    alerta.estado = "Notificada" if notificados > 0 else "Error"
    db.commit()

    return {
        "id_alerta": alerta.id_alerta,
        "id_evento": evento.id_evento,
        "estado": alerta.estado,
        "destinatarios_total": len(destinatarios),
        "destinatarios_notificados": notificados,
        "destinatarios_errores": errores,
    }