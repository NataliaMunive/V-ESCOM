from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date, time


# ─── Persona autorizada ───────────────────────────────────────────────────────

class CrearPersonaAutorizada(BaseModel):
    nombre: str
    apellidos: str
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: Optional[str] = "Profesor"


class DatosPersonaAutorizada(BaseModel):
    id_persona: int
    nombre: str
    apellidos: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: str
    ruta_rostro: Optional[str] = None
    tiene_embedding: bool = False
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdPersonaAutorizada(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: Optional[str] = None


# ─── Reconocimiento ───────────────────────────────────────────────────────────

class ResultadoReconocimiento(BaseModel):
    tipo_acceso: str                    # "Autorizado" | "No Autorizado"
    similitud: float
    id_persona: Optional[int] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    id_evento: int


# ─── Evento de acceso ─────────────────────────────────────────────────────────

class DatosEvento(BaseModel):
    id_evento: int
    id_camara: Optional[int] = None
    id_persona: Optional[int] = None
    tipo_acceso: str
    fecha: Optional[date] = None
    hora: Optional[time] = None
    similitud: Optional[float] = None

    class Config:
        from_attributes = True

