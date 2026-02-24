from sqlalchemy import Column, Integer, String, ForeignKey
from app.bd import Base


class Entrada(Base):
    __tablename__ = "entradas"

    id_entrada = Column(Integer, primary_key=True, index=True)
    id_camara = Column(Integer, ForeignKey("camaras.id_camara"), nullable=True)
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"), nullable=True)
    nombre = Column(String(100), nullable=True)
    tipo = Column(String(30), nullable=True)
    estado = Column(String(20), default="Activa")
