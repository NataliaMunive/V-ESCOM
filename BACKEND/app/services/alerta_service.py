"""
Servicio de Gestión de Alertas - V-ESCOM

Contiene la lógica de negocio para consultar y actualizar incidencias.
Implementa consultas complejas uniendo las tablas de Alertas y Eventos
para proporcionar un contexto completo de cada detección.

manejo de errores:
- Si la alerta no existe, se lanza un HTTPException 404.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.administrador import Administrador
from app.models.alerta import Alerta
from app.models.camara import Camara
from app.models.evento import EventoAcceso
from app.models.notificacion import Notificacion
from app.models.persona_autorizada import PersonaAutorizada


def _obtener_destinatarios_evento(db: Session, evento: EventoAcceso | None) -> list[str]:
    """
    Reconstuye los destinatarios previstos para una alerta a partir del evento.
    Se usa como respaldo cuando aún no existen filas de Notificacion persistidas.
    """
    if not evento:
        return []

    camara = (
        db.query(Camara)
        .filter(Camara.id_camara == evento.id_camara)
        .first()
    )
    id_cubiculo = camara.id_cubiculo if camara else None

    destinatarios = []
    admins = db.query(Administrador).filter(Administrador.telegram_chat_id.isnot(None)).all()
    for admin in admins:
        destinatarios.append(f"Admin: {admin.nombre} {admin.apellidos}")

    if id_cubiculo is not None:
        personas = (
            db.query(PersonaAutorizada)
            .filter(PersonaAutorizada.telegram_chat_id.isnot(None))
            .filter(PersonaAutorizada.id_cubiculo == id_cubiculo)
            .all()
        )
        for persona in personas:
            destinatarios.append(f"Persona autorizada: {persona.nombre} {persona.apellidos}")

    return destinatarios


def _detalle_destinatario_actual(db: Session, notificacion: Notificacion) -> str:
    """
    Devuelve el nombre del destinatario y su estado actual de Telegram.
    Usa el chat_id guardado en Notificacion.telefono como llave de búsqueda.
    """
    chat_id = (notificacion.telefono or '').strip()
    if chat_id:
        admin = (
            db.query(Administrador)
            .filter(Administrador.telegram_chat_id == chat_id)
            .first()
        )
        if admin:
            return f"Admin: {admin.nombre} {admin.apellidos} · Telegram actual: vinculado"

        persona = (
            db.query(PersonaAutorizada)
            .filter(PersonaAutorizada.telegram_chat_id == chat_id)
            .first()
        )
        if persona:
            return f"Persona autorizada: {persona.nombre} {persona.apellidos} · Telegram actual: vinculado"

    nombre = notificacion.destinatario or 'Destinatario'
    return f"{nombre} · Telegram actual: no vinculado"


def _esta_vinculado_actual(db: Session, notificacion: Notificacion) -> bool:
    chat_id = (notificacion.telefono or '').strip()
    if not chat_id:
        return False

    admin = (
        db.query(Administrador)
        .filter(Administrador.telegram_chat_id == chat_id)
        .first()
    )
    if admin:
        return True

    persona = (
        db.query(PersonaAutorizada)
        .filter(PersonaAutorizada.telegram_chat_id == chat_id)
        .first()
    )
    return persona is not None


def _a_alerta_detalle(db: Session, alerta: Alerta, evento: EventoAcceso | None) -> dict:
    """
    Función auxiliar para aplanar (denormalizar) los datos de Alerta y Evento.
    Retorna un diccionario compatible con el esquema 'DatosAlerta'.
    """
    notificaciones = (
        db.query(Notificacion)
        .filter(Notificacion.id_alerta == alerta.id_alerta)
        .order_by(Notificacion.id_notificacion.asc())
        .all()
    )
    notificaciones_validas = [n for n in notificaciones if _esta_vinculado_actual(db, n)]
    enviadas = [n for n in notificaciones_validas if n.estado == "Enviado"]
    errores = [n for n in notificaciones_validas if n.estado == "Error"]
    destinatarios_notificados = [n.destinatario for n in enviadas if n.destinatario]
    destinatarios_notificados_detalle = [
        _detalle_destinatario_actual(db, n)
        for n in enviadas
    ]

    if not notificaciones_validas and alerta.estado == "Notificada":
        destinatarios_notificados = _obtener_destinatarios_evento(db, evento)
        total_destinatarios = len(destinatarios_notificados)
        enviados_total = total_destinatarios
        errores_total = 0
    else:
        total_destinatarios = len(notificaciones_validas)
        enviados_total = len(enviadas)
        errores_total = len(errores)

    return {
        "id_alerta": alerta.id_alerta,
        "id_evento": alerta.id_evento,
        "tipo_alerta": alerta.tipo_alerta,
        "estado": alerta.estado,
        # Si el evento no existe (huérfano), se retornan valores nulos de forma segura
        "tipo_acceso": evento.tipo_acceso if evento else None,
        "id_camara": evento.id_camara if evento else None,
        "similitud": evento.similitud if evento else None,
        "fecha": alerta.fecha,
        "hora": alerta.hora,
        "notificaciones_total": total_destinatarios,
        "notificaciones_enviadas": enviados_total,
        "notificaciones_errores": errores_total,
        "destinatarios_notificados": destinatarios_notificados,
        "destinatarios_notificados_detalle": destinatarios_notificados_detalle,
    }


def obtener_alertas(
    db: Session,
    estado: str | None = None,
    tipo_alerta: str | None = None,
    tipo_acceso: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Realiza una búsqueda avanzada de alertas con filtrado dinámico.
    Utiliza un OUTER JOIN para asegurar que se vean las alertas incluso si hubiera problemas con el registro del evento.
    """
    # Iniciam la consulta base uniendo Alerta con su Evento correspondiente
    query = (
        db.query(Alerta, EventoAcceso)
        .outerjoin(EventoAcceso, EventoAcceso.id_evento == Alerta.id_evento)
    )

    # Aplicación de filtros dinámicos según los parámetros de la URL
    if estado:
        query = query.filter(Alerta.estado == estado)
    if tipo_alerta:
        query = query.filter(Alerta.tipo_alerta == tipo_alerta)
    if tipo_acceso:
        query = query.filter(EventoAcceso.tipo_acceso == tipo_acceso)

    # Ordenamos por las más recientes (ID descendente)
    filas = (
        query.order_by(Alerta.id_alerta.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_a_alerta_detalle(db, alerta, evento) for alerta, evento in filas]


def obtener_resumen_alertas(
    db: Session,
    estado: str | None = None,
    tipo_alerta: str | None = None,
    tipo_acceso: str | None = None,
):
    """
    Devuelve métricas agregadas sin aplicar paginación.
    """
    base = (
        db.query(Alerta, EventoAcceso)
        .outerjoin(EventoAcceso, EventoAcceso.id_evento == Alerta.id_evento)
    )

    if estado:
        base = base.filter(Alerta.estado == estado)
    if tipo_alerta:
        base = base.filter(Alerta.tipo_alerta == tipo_alerta)
    if tipo_acceso:
        base = base.filter(EventoAcceso.tipo_acceso == tipo_acceso)

    total = base.count()
    no_autorizados = base.filter(EventoAcceso.tipo_acceso == 'No Autorizado').count()
    autorizados = base.filter(EventoAcceso.tipo_acceso == 'Autorizado').count()
    tasa_intrusion = round((no_autorizados / total) * 100, 1) if total else 0.0

    return {
        'total': total,
        'no_autorizados': no_autorizados,
        'autorizados': autorizados,
        'tasa_intrusion': tasa_intrusion,
    }


def obtener_alerta(db: Session, id_alerta: int):
    """Consulta una alerta específica o lanza 404 si no existe."""
    alerta = db.query(Alerta).filter(Alerta.id_alerta == id_alerta).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alerta


def actualizar_alerta(db: Session, id_alerta: int, datos):
    """
    Actualiza los campos de una alerta de forma dinámica.
    - exclude_unset=True: Solo modifica los campos que el usuario envió realmente.
    """
    alerta = obtener_alerta(db, id_alerta)

    # Actualización masiva de atributos del modelo SQLAlchemy
    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(alerta, key, value)

    db.commit()
    db.refresh(alerta)

    # Recuperamos el evento asociado para devolver el detalle completo actualizado
    evento = (
        db.query(EventoAcceso)
        .filter(EventoAcceso.id_evento == alerta.id_evento)
        .first()
    )
    return _a_alerta_detalle(db, alerta, evento)


def obtener_detalle_notificacion_alerta(db: Session, id_alerta: int) -> dict:
    """
    Devuelve el detalle de destinatarios para una alerta específica.
    """
    alerta = obtener_alerta(db, id_alerta)
    evento = (
        db.query(EventoAcceso)
        .filter(EventoAcceso.id_evento == alerta.id_evento)
        .first()
    )
    return _a_alerta_detalle(db, alerta, evento)