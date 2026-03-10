from pydantic import BaseModel, EmailStr
from typing import Optional

class CrearProfesor(BaseModel):
    nombre: str
    correo: EmailStr
    telefono: str
    id_cubiculo: int

class UpdProfesor(BaseModel):
    nombre: Optional[str]
    correo: Optional[EmailStr]
    telefono: Optional[str]
    id_cubiculo: Optional[int]
    activo: Optional[bool]

class DatosProfesor(BaseModel):
    id_profesor: int
    nombre: str
    correo: str
    telefono: Optional[str] = None
    id_cubiculo: int
    activo: bool

    class Config:
        from_attributes = True
