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

from app.models.alerta import Alerta
from app.models.evento import EventoAcceso


def _a_alerta_detalle(alerta: Alerta, evento: EventoAcceso | None) -> dict:
    """
    Función auxiliar para aplanar (denormalizar) los datos de Alerta y Evento.
    Retorna un diccionario compatible con el esquema 'DatosAlerta'.
    """
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

    return [_a_alerta_detalle(alerta, evento) for alerta, evento in filas]


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
    return _a_alerta_detalle(alerta, evento)