"""
Modelo de Datos: Embeddings - V-ESCOM

Almacena las representaciones vectoriales (huellas faciales) de las personas.
Es el componente crítico para la comparación biométrica en tiempo real.
"""

from sqlalchemy import Column, Integer, LargeBinary, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Embedding(Base):
    """
    Entidad que guarda los vectores característicos generados por el modelo de IA.
    
    El proceso de identificación consiste en comparar un rostro detectado 
    contra los registros de esta tabla mediante distancia euclidiana o similitud de coseno.
    """
    __tablename__ = "embeddings"

    # Identificador único del registro de embedding
    id_embedding = Column(Integer, primary_key=True, index=True)
    
    # Relación 1:1 con la persona autorizada
    # Garantiza que no existan múltiples vectores de referencia para un mismo usuario
    id_persona = Column(Integer, ForeignKey("personas_autorizadas.id_persona"), unique=True, nullable=False)
    
    # Datos binarios del vector (usualmente un array de 128 o 512 dimensiones)
    # Se recomienda serializar con pickle o numpy.tobytes() antes de guardar
    vector = Column(LargeBinary, nullable=False)
    
    # Registro histórico de cuándo se generó o actualizó la biometría
    fecha_registro = Column(TIMESTAMP, server_default=func.now())