"""
Modelo de Datos: Personas Autorizadas - V-ESCOM

Entidad central para el reconocimiento facial. Almacena la identidad,
el rol y la firma biométrica (embedding) del personal con acceso permitido.
"""

from sqlalchemy import Column, Integer, String, LargeBinary, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base

class PersonaAutorizada(Base):
    """
    Representa a cualquier individuo validado por el sistema (Profesores, Alumnos, Staff).
    
    Contiene el vector de características faciales que el motor de IA utiliza para realizar la clasificación en los eventos de acceso.
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
    
    # Firma matemática del rostro (Vector de 512 dimensiones)
    # Almacenado como binario para optimizar la velocidad de comparación
    embedding = Column(LargeBinary)
    
    # Auditoría de alta en el sistema
    fecha_registro = Column(TIMESTAMP, server_default=func.now())