"""
Configuración del Motor de Base de Datos y Servicios Core del Sistema V-ESCOM.

Este módulo centraliza la conexión via SQLAlchemy y define la lógica de negocio para:
1. Gestión de Entidades: CRUD para Profesores y Cámaras con Soft Delete.
2. Reconocimiento Facial: Procesamiento de embeddings, identificación y registro de eventos.
3. Sistema de Notificaciones: Alertas automáticas vía SMS para accesos e intrusiones.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from pgvector.psycopg2 import register_vector

# ─── Configuracion del entorno ──────────────────────────────────────────────────
# Se busca el archivo .env en la raíz del proyecto (directorio superior al backend)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# ─── Config de SQLALCHEMY ───────────────────────────────────────────────
# Creamos el motor de conexión y la fábrica de sesiones
engine = create_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def _register_vector_type(dbapi_connection, connection_record):
    register_vector(dbapi_connection)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para la creación de modelos ORM
Base = declarative_base()

def get_db():
    """
    Generador de sesiones de base de datos (Dependency Injection).
    Asegura que la conexión se cierre automáticamente tras completar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()