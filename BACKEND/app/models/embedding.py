from sqlalchemy import Column, Integer, LargeBinary
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    vector = Column(LargeBinary, nullable=False)
