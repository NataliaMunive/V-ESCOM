from sqlalchemy import Column, Integer, LargeBinary, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Embedding(Base):
    __tablename__ = "embeddings"

    id_embedding = Column(Integer, primary_key=True, index=True)
    id_persona = Column(Integer, ForeignKey("personas_autorizadas.id_persona"), unique=True, nullable=False)
    vector = Column(LargeBinary, nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())
