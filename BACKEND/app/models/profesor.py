from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Profesor(Base):
    __tablename__ = "profesores"

    id_profesor = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    activo = Column(Boolean, default=True)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())
