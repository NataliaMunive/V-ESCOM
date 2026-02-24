from pydantic import BaseModel
from typing import Optional

class CrearCamara(BaseModel):
    nombre: str
    direccion_ip: Optional[str] = None
    ubicacion: Optional[str]
    id_cubiculo: int
    estado: Optional[str] = "Activa"

class UpdCamara(BaseModel):
    nombre: Optional[str]
    direccion_ip: Optional[str]
    ubicacion: Optional[str]
    id_cubiculo: Optional[int]
    activa: Optional[bool]
    estado: Optional[str]

class DatosCamara(BaseModel):
    id_camara: int
    nombre: str
    direccion_ip: Optional[str]
    ubicacion: Optional[str]
    id_cubiculo: int
    activa: bool
    estado: Optional[str]

    class Config:
        from_attributes = True
