"""
Esquemas de Validación (Pydantic) para Autenticación - V-ESCOM

Define las estructuras de datos para las peticiones y respuestas del módulo de seguridad. Estos modelos aseguran la integridad de los datos y generan automáticamente la documentación OpenAPI (Swagger).
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# ─── Autenticacion ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Cuerpo de la petición para inicio de sesión estándar."""
    email: EmailStr
    contrasena: str

class TokenResponse(BaseModel):
    """Respuesta exitosa de autenticación que entrega el JWT."""
    access_token: str
    token_type: str = "bearer"


# ─── Administracion de usuarios (CRUD) ────────────────────────────────────────

class CrearAdmin(BaseModel):
    """Datos obligatorios para registrar un nuevo administrador en el sistema."""
    nombre: str
    apellidos: str
    email: EmailStr
    # El teléfono es opcional pero recomendado para recibir alertas SMS
    telefono: Optional[str] = None
    # La contraseña viaja en texto plano y debe ser hasheada en la capa de servicios
    contrasena: str


class DatosAdmin(BaseModel):
    """
    Esquema de salida (Response) para perfiles de administrador.
    No incluye la contraseña por motivos de seguridad.
    """
    id_admin: int
    nombre: str
    apellidos: str
    email: str
    telefono: Optional[str] = None
    fotografia: Optional[str] = None
    activo: bool
    fecha_registro: Optional[datetime] = None

    class Config:
        # Permite que Pydantic lea los datos directamente desde el objeto de SQLAlchemy
        from_attributes = True


class UpdAdmin(BaseModel):
    """
    Esquema para actualizaciones parciales.
    """
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    # Si se incluye, el servicio detectará el cambio y generará un nuevo hash
    contrasena: Optional[str] = None