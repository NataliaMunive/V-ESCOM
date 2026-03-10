"""
Modelo de Datos: Administradores - V-ESCOM

Representa a los usuarios con privilegios elevados encargados de gestionar 
el sistema y recibir alertas de seguridad críticas.
"""

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from app.bd import Base

class Administrador(Base):
    """
    Entidad que almacena la información de acceso y perfil de los administradores.
    
    Incluye mecanismos de control para seguridad de cuenta (bloqueo por intentos).
    """
    __tablename__ = "administradores"

    # Identificador único y datos personales
    id_admin = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    apellidos = Column(String(80), nullable=False)
    
    # Identidad y Comunicación
    # El email es el 'username' principal para el login
    email = Column(String(100), unique=True, nullable=False, index=True)
    # Almacenado en formato E.164 para integración con Twilio
    telefono = Column(String(20))
    # Ruta al archivo de imagen para el perfil del administrador
    fotografia = Column(String(255)) 
    
    # Seguridad de Acceso
    # Almacena el hash irreversible generado con BCrypt
    contrasena = Column(String(255), nullable=False)
    # Soft Delete: Permite desactivar acceso sin perder el historial
    activo = Column(Boolean, default=True)
    
    # Control de Fuerza Bruta
    # Contador para restringir acceso tras múltiples fallos
    intentos_fallidos = Column(Integer, default=0)
    # Marca de tiempo para desbloqueo automático temporal
    bloqueado_hasta = Column(TIMESTAMP, nullable=True)
    
    # Auditoría
    fecha_registro = Column(TIMESTAMP, server_default=func.now())