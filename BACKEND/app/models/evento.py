"""
Modelos de Registro de Actividad - V-ESCOM

Gestionan el histórico de detecciones del sistema, diferenciando entre 
accesos de personal conocido y registros de intrusos.
"""

from sqlalchemy import Column, Integer, String, Float, Date, Time, LargeBinary, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base

class EventoAcceso(Base):
    """
    Bitácora general de detecciones realizadas por el motor de IA.
    
    Registra tanto los éxitos de reconocimiento como los fallos (intrusiones), almacenando el nivel de confianza (similitud) de la predicción.
    """
    __tablename__ = "eventos_acceso"

    id_evento = Column(Integer, primary_key=True, index=True)
    
    # Origen del evento
    id_camara = Column(Integer, ForeignKey("camaras.id_camara"))
    
    # Identidad detectada (nulo si es 'No Autorizado')
    id_persona = Column(Integer, ForeignKey("personas_autorizadas.id_persona"), nullable=True)
    
    # Clasificación: 'Autorizado' o 'No Autorizado' (Intrusión)
    tipo_acceso = Column(String(20))
    
    # Estampas de tiempo automáticas
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
    
    # Puntaje de confianza del reconocimiento (ej. 0.98 para alta certeza)
    similitud = Column(Float)


class PersonaNoAutorizada(Base):
    """
    Registro de evidencia para individuos no reconocidos por el sistema.
    
    Almacena la ruta de la fotografía capturada y su embedding para permitir búsquedas posteriores de 'reincidentes' no autorizados.
    """
    __tablename__ = "personas_no_autorizadas"

    id_pna = Column(Integer, primary_key=True, index=True)
    
    # Momento exacto de la captura del intruso
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
    
    # Ruta en el servidor donde se guardó el frame de la captura
    ruta_imagen_captura = Column(String(255))
    
    # Vector característico del rostro desconocido para comparaciones futuras
    embedding_detectado = Column(LargeBinary)