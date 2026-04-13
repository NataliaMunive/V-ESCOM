"""
Modelo de Datos: Personas Autorizadas - V-ESCOM

Entidad central para el reconocimiento facial. Almacena la identidad
y metadatos de las personas con acceso permitido.
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base

class PersonaAutorizada(Base):
    """
    Representa a cualquier individuo validado por el sistema (Profesores, Alumnos, Staff).
    
    Los embeddings faciales asociados se almacenan en la tabla rostros_autorizados
    para permitir múltiples firmas por persona.
    """
    __tablename__ = "personas_autorizadas"

    # Identificador único de la persona
    id_persona = Column(Integer, primary_key=True, index=True)
    
    # Datos personales y de contacto
    nombre = Column(String(50), nullable=False)
    apellidos = Column(String(80), nullable=False)
    email = Column(String(100))
    
    # Teléfono en formato E.164 para notificaciones directas
    telefono = Column(String(20))
    
    # Ubicación física principal asignada
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    
    # Clasificación del usuario (ej. 'Profesor', 'Investigador', 'Administrativo')
    rol = Column(String(30), default="Profesor")
    
    # Gestión Biométrica
    # Ruta al archivo físico de la imagen utilizada para el registro inicial
    ruta_rostro = Column(String(255))
    
    # Auditoría de alta en el sistema
    fecha_registro = Column(TIMESTAMP, server_default=func.now())