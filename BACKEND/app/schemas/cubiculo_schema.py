"""
Esquemas de Validación (Pydantic) para Cubículos - V-ESCOM

Define la estructura de datos para los espacios físicos monitoreados.
"""

from pydantic import BaseModel, Field
from typing import Optional

class CrearCubiculo(BaseModel):
    """Requisitos para registrar un nuevo cubículo."""
    numero_cubiculo: str = Field(..., example="A-101")
    capacidad: int = Field(..., gt=0, example=10)
    responsable: Optional[str] = Field(None, example="Dr. Juan Pérez")

class UpdCubiculo(BaseModel):
    """Campos para actualizar un cubículo."""
    numero_cubiculo: Optional[str] = None
    capacidad: Optional[int] = Field(None, gt=0)
    responsable: Optional[str] = None

class DatosCubiculo(BaseModel):
    """Esquema de salida para cubículos."""
    id_cubiculo: int
    numero_cubiculo: str
    capacidad: int
    responsable: Optional[str]

    class Config:
        from_attributes = True