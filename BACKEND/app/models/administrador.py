from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base


class Administrador(Base):
    __tablename__ = "administradores"

    id_admin = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    apellidos = Column(String(80), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    telefono = Column(String(20))
    fotografia = Column(String(255))        # ruta relativa
    contrasena = Column(String(255), nullable=False)  # hash bcrypt
    activo = Column(Boolean, default=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(TIMESTAMP, nullable=True)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())