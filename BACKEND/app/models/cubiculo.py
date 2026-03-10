"""
Modelo de Datos: Cubículos - V-ESCOM

Define los espacios físicos monitoreados. Actúa como el eje central que vincula a los profesores con los dispositivos de videovigilancia (Cámaras).
"""

from sqlalchemy import Column, Integer, String
from app.bd import Base

class Cubiculo(Base):
    """
    Entidad que representa un cubículo dentro de las instalaciones de ESCOM.
    
    Esta tabla es fundamental para la segmentación de notificaciones:
    los eventos ocurridos en cámaras vinculadas a este ID se reportarán
    a los profesores asociados al mismo ID.
    """
    __tablename__ = "cubiculos"

    # Identificador único interno para relaciones (Foreign Keys)
    id_cubiculo = Column(Integer, primary_key=True, index=True)
    
    # Identificación oficial
    # Se marca como único para evitar duplicidad de registros físicos
    numero_cubiculo = Column(String(20), unique=True, nullable=False)
    
    # Cantidad máxima de personas permitidas o asignadas
    capacidad = Column(Integer, nullable=False)
    
    # Nombre del jefe de área o profesor principal a cargo del espacio
    responsable = Column(String(100), nullable=True)