"""
Esquemas de Validación (Pydantic) para Cámaras - V-ESCOM

Define la estructura de datos para el inventario de hardware. 
Asegura que cada cámara esté correctamente vinculada a un cubículo 
y posea una identificación de red válida.
"""

from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional

# ─── Esquemas de camara ───────────────────────────────────────────────────────

class CrearCamara(BaseModel):
    """Requisitos mínimos para registrar un nuevo dispositivo de captura."""
    nombre: str = Field(..., example="Cámara Acceso A-1")
    # Soporta formatos IPv4 o IPv6
    direccion_ip: Optional[IPvAnyAddress] = Field(None, example="192.168.1.50")
    ubicacion: Optional[str] = Field(None, example="Esquina superior derecha, puerta")
    # ID del cubículo al que pertenece (debe existir en la DB)
    id_cubiculo: int
    estado: Optional[str] = "Activa"

class UpdCamara(BaseModel):
    """
    Campos permitidos para edición. 
    Permite actualizaciones parciales (PATCH) del dispositivo.
    """
    nombre: Optional[str] = None
    direccion_ip: Optional[IPvAnyAddress] = None
    ubicacion: Optional[str] = None
    id_cubiculo: Optional[int] = None
    # Permite habilitar o deshabilitar el procesamiento de IA
    activa: Optional[bool] = None
    estado: Optional[str] = None

class DatosCamara(BaseModel):
    """
    Esquema de salida para visualización en el Frontend.
    Incluye metadatos completos y el estado de activación.
    """
    id_camara: int
    nombre: str
    direccion_ip: Optional[IPvAnyAddress]
    ubicacion: Optional[str]
    id_cubiculo: int
    activa: bool
    estado: Optional[str]

    class Config:
        # Habilita la compatibilidad con modelos de SQLAlchemy
        from_attributes = True