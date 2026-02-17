from pydantic import BaseModel, EmailStr
from typing import Optional

class ProfesorCreate(BaseModel):
    nombre: str
    correo: EmailStr
    id_cubiculo: int

class ProfesorUpdate(BaseModel):
    nombre: Optional[str]
    correo: Optional[EmailStr]
    id_cubiculo: Optional[int]
    activo: Optional[bool]

class ProfesorResponse(BaseModel):
    id_profesor: int
    nombre: str
    correo: str
    id_cubiculo: int
    activo: bool

    class Config:
        from_attributes = True
