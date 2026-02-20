from sqlalchemy import Column, Integer, String, LargeBinary, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.bd import Base


class PersonaAutorizada(Base):
    __tablename__ = "personas_autorizadas"

    id_persona = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    apellidos = Column(String(80), nullable=False)
    email = Column(String(100))
    telefono = Column(String(20))
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"))
    rol = Column(String(30), default="Profesor")
    ruta_rostro = Column(String(255))       # ruta de imagen de referencia
    embedding = Column(LargeBinary)         # vector 512-d serializado
    fecha_registro = Column(TIMESTAMP, server_default=func.now())