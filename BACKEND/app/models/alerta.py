from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.sql import func
from app.bd import Base


class Alerta(Base):
    __tablename__ = "alertas"

    id_alerta = Column(Integer, primary_key=True, index=True)
    id_evento = Column(Integer, ForeignKey("eventos_acceso.id_evento"), nullable=False)
    tipo_alerta = Column(String(50), default="Intrusion")
    estado = Column(String(20), default="Pendiente")
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
