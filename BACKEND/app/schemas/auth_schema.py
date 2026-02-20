from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    contrasena: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Admin CRUD ───────────────────────────────────────────────────────────────

class CrearAdmin(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    telefono: Optional[str] = None
    contrasena: str     # texto plano, se hashea en el servicio


class DatosAdmin(BaseModel):
    id_admin: int
    nombre: str
    apellidos: str
    email: str
    telefono: Optional[str] = None
    fotografia: Optional[str] = None
    activo: bool
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdAdmin(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    contrasena: Optional[str] = None    # si se envía, se re-hashea