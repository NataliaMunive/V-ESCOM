"""
Modelo de Datos: Notificaciones - V-ESCOM

Registra el historial individual de cada mensaje enviado (SMS) como respuesta 
a una alerta. Permite auditar la eficacia de la comunicación del sistema.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.sql import func
from app.bd import Base

class Notificacion(Base):
    """
    Entidad que detalla el envío de alertas a destinatarios específicos.
    
    Una sola 'Alerta' puede generar múltiples 'Notificaciones' (ej. una para el administrador y otra para el profesor del cubículo).
    """
    __tablename__ = "notificaciones"

    # Identificador único del registro de envío
    id_notificacion = Column(Integer, primary_key=True, index=True)
    
    # Relación con la alerta que originó este envío
    id_alerta = Column(Integer, ForeignKey("alertas.id_alerta"), nullable=False)
    
    # Nombre de la persona (Admin o Profesor) que recibe el mensaje
    destinatario = Column(String(100), nullable=True)
    
    # Canal de comunicación utilizado (por defecto: 'SMS')
    medio = Column(String(20), nullable=True)
    
    # Estado del envío: 'Enviado', 'Error', 'No configurado', 'Sin destinatario'
    estado = Column(String(20), nullable=True)
    
    # Número telefónico en formato E.164 al que se disparó el mensaje
    telefono = Column(String(20), nullable=True)
    
    # Estampas de tiempo para auditoría de tiempos de respuesta
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())