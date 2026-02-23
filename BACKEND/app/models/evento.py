from sqlalchemy import Column, Integer, String, Float, Date, Time, LargeBinary, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base


class EventoAcceso(Base):
    __tablename__ = "eventos_acceso"

    id_evento = Column(Integer, primary_key=True, index=True)
    id_camara = Column(Integer, ForeignKey("camaras.id_camara"))
    id_persona = Column(Integer, ForeignKey("personas_autorizadas.id_persona"), nullable=True)
    tipo_acceso = Column(String(20))    # "Autorizado" | "No Autorizado"
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
    similitud = Column(Float)           # 0.0 – 1.0


class PersonaNoAutorizada(Base):
    __tablename__ = "personas_no_autorizadas"

    id_pna = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
    ruta_imagen_captura = Column(String(255))
    embedding_detectado = Column(LargeBinary)