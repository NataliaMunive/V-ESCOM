"""
Modelo de Datos: Cámaras - V-ESCOM

Representa los dispositivos de captura de video distribuidos en la unidad.
Vincula el hardware físico (IP) con la ubicación lógica (Cubículo).
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Camara(Base):
    """
    Entidad que gestiona la configuración y el estado de las cámaras de vigilancia.
    
    Permite filtrar qué eventos pertenecen a qué cubículo y validar si un 
    dispositivo debe ser procesado por el motor de reconocimiento.
    """
    __tablename__ = "camaras"

    # Identificador único del dispositivo
    id_camara = Column(Integer, primary_key=True, index=True)
    
    # Nombre descriptivo (ej. 'Cámara Acceso Principal')
    nombre = Column(String, nullable=False)
    
    # Dirección IPv4 o IPv6 para la conexión con el stream de video
    direccion_ip = Column(String(45), nullable=True)
    
    # Descripción física del lugar donde está instalada
    ubicacion = Column(String)
    
    # Relación jerárquica: Una cámara pertenece a un cubículo específico
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    
    # Control de flujo: Define si el sistema debe procesar imágenes de esta cámara
    activa = Column(Boolean, default=True)
    
    # Estado operativo detallado (ej. 'Activa', 'Inactiva', 'Desconectada')
    estado = Column(String(20), default="Activa")
    
    # Auditoría de creación del registro
    fecha_registro = Column(TIMESTAMP, server_default=func.now())