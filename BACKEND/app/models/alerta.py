"""
Modelo de Datos: Alertas - V-ESCOM

Registra las incidencias de seguridad generadas por el motor de reconocimiento.
Cada alerta está vinculada de forma obligatoria a un evento de acceso.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.sql import func
from app.bd import Base

class Alerta(Base):
    """
    Entidad que gestiona el ciclo de vida de una notificación de seguridad.
    
    Estados típicos: 
    - 'Pendiente': Creada pero sin notificaciones enviadas.
    - 'Notificada': SMS enviado exitosamente a los responsables.
    - 'Error': Fallo en el servicio de mensajería.
    """
    __tablename__ = "alertas"

    # Identificador único de la alerta
    id_alerta = Column(Integer, primary_key=True, index=True)
    
    # Relación con el evento origen (llave foránea)
    id_evento = Column(Integer, ForeignKey("eventos_acceso.id_evento"), nullable=False)
    
    # Categorización de la alerta (ej. 'Intrusion', 'Acceso No Autorizado')
    tipo_alerta = Column(String(50), default="Intrusion")
    
    # Estado actual del proceso de notificación
    estado = Column(String(20), default="Pendiente")
    
    # Estampas de tiempo automáticas generadas por el servidor de base de datos
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())