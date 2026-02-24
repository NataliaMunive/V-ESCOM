from sqlalchemy import Column, Integer, String
from app.bd import Base


class Cubiculo(Base):
    __tablename__ = "cubiculos"

    id_cubiculo = Column(Integer, primary_key=True, index=True)
    numero_cubiculo = Column(String(20), unique=True, nullable=False)
    capacidad = Column(Integer, nullable=False)
    responsable = Column(String(100), nullable=True)
