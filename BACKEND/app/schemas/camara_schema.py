from pydantic import BaseModel
from typing import Optional

class CrearCamara(BaseModel):
    nombre: str
    ubicacion: Optional[str]
    id_cubiculo: int

class UpdCamara(BaseModel):
    nombre: Optional[str]
    ubicacion: Optional[str]
    id_cubiculo: Optional[int]
    activa: Optional[bool]

class DatosCamara(BaseModel):
    id_camara: int
    nombre: str
    ubicacion: Optional[str]
    id_cubiculo: int
    activa: bool

    class Config:
        from_attributes = True
