"""
Modelo de Datos: Rostros Autorizados - V-ESCOM

Permite almacenar múltiples firmas faciales por persona autorizada.
"""

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func

from app.bd import Base


class RostroAutorizado(Base):
    __tablename__ = "rostros_autorizados"

    id_rostro = Column(Integer, primary_key=True, index=True)
    id_persona = Column(
        Integer,
        ForeignKey("personas_autorizadas.id_persona", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = Column(VECTOR(512), nullable=False)
    descripcion = Column(String(50))
    ruta_imagen = Column(String(255))
    fecha_captura = Column(TIMESTAMP, server_default=func.now())
