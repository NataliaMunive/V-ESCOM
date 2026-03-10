"""
Modelo de Datos: Profesores - V-ESCOM

Gestiona la información de contacto y adscripción de los docentes.
Es la entidad principal de destino para las notificaciones de acceso y seguridad
de los cubículos asignados.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Profesor(Base):
    """
    Entidad que representa a un docente responsable de un espacio físico.
    
    A través de esta tabla, el sistema identifica a quién contactar vía SMS 
    cuando se genera una alerta en un cubículo específico.
    """
    __tablename__ = "profesores"

    # Identificador único del profesor
    id_profesor = Column(Integer, primary_key=True, index=True)
    
    # Datos de identidad
    nombre = Column(String, nullable=False)
    
    # Credenciales y contacto (Garantizan que no haya duplicados)
    correo = Column(String, unique=True, nullable=False)
    # Almacenado en formato E.164 para compatibilidad con Twilio
    telefono = Column(String(20), unique=True)
    
    # Relación de adscripción: Define qué cubículo tiene bajo su resguardo
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    
    # Soft Delete: Permite dar de baja a un profesor sin borrar su historial de eventos
    activo = Column(Boolean, default=True)
    
    # Auditoría de alta en el sistema
    fecha_registro = Column(TIMESTAMP, server_default=func.now())