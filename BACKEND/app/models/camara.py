from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Camara(Base):
    __tablename__ = "camaras"

    id_camara = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    direccion_ip = Column(String(45), nullable=True)
    ubicacion = Column(String)
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    activa = Column(Boolean, default=True)
    estado = Column(String(20), default="Activa")
    fecha_registro = Column(TIMESTAMP, server_default=func.now())
