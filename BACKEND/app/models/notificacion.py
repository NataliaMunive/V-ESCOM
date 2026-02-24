from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.sql import func
from app.bd import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id_notificacion = Column(Integer, primary_key=True, index=True)
    id_alerta = Column(Integer, ForeignKey("alertas.id_alerta"), nullable=False)
    destinatario = Column(String(100), nullable=True)
    medio = Column(String(20), nullable=True)
    estado = Column(String(20), nullable=True)
    telefono = Column(String(20), nullable=True)
    fecha = Column(Date, server_default=func.current_date())
    hora = Column(Time, server_default=func.current_time())
