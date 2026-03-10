"""
Modelo de Datos: Logs del Sistema - V-ESCOM

Funciona como el diario operativo de la aplicación. Registra eventos internos,
errores de ejecución y trazabilidad de procesos de fondo.
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base

class LogSistema(Base):
    """
    Entidad de auditoría y diagnóstico.
    
    Permite reconstruir la secuencia de eventos ante fallos técnicos o de seguridad,
    vinculando procesos de software con eventos físicos de acceso.
    """
    __tablename__ = "logs_sistema"

    # Identificador único del log
    id_log = Column(Integer, primary_key=True, index=True)
    
    # Relación opcional con un evento de acceso
    id_evento = Column(Integer, ForeignKey("eventos_acceso.id_evento"), nullable=True)
    
    # Gravedad del evento (ej. 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    nivel = Column(String(20), nullable=True)
    
    # Componente que genera el log (ej. 'Motor_IA', 'Servicio_SMS', 'Auth_Module')
    origen = Column(String(50), nullable=True)
    
    # Descripción detallada del suceso o traza del error (Stacktrace)
    mensaje = Column(Text, nullable=True)
    
    # Categoría del log (ej. 'Conexión_DB', 'Reconocimiento', 'Sistema')
    tipo = Column(String(30), nullable=True)
    
    # Marca de tiempo precisa de la ocurrencia
    fecha = Column(TIMESTAMP, server_default=func.now())