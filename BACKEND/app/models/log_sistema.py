from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base


class LogSistema(Base):
    __tablename__ = "logs_sistema"

    id_log = Column(Integer, primary_key=True, index=True)
    id_evento = Column(Integer, ForeignKey("eventos_acceso.id_evento"), nullable=True)
    nivel = Column(String(20), nullable=True)
    origen = Column(String(50), nullable=True)
    mensaje = Column(Text, nullable=True)
    tipo = Column(String(30), nullable=True)
    fecha = Column(TIMESTAMP, server_default=func.now())
