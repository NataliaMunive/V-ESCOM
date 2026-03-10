"""
Esquemas de Validación (Pydantic) para Reconocimiento y Eventos - V-ESCOM

Define la estructura de los datos biométricos y el registro de acceso.
Maneja la información resultante de la comparación de rostros y la
trazabilidad de los eventos de seguridad detectados por las cámaras.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date, time

# ─── Persona autorizada ──────────────────────────────────────────

class CrearPersonaAutorizada(BaseModel):
    """Datos básicos para el pre-registro de una persona antes de generar su embedding."""
    nombre: str
    apellidos: str
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: Optional[str] = "Profesor"

class DatosPersonaAutorizada(BaseModel):
    """Información completa del perfil autorizado, incluyendo estado biométrico."""
    id_persona: int
    nombre: str
    apellidos: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: str
    ruta_rostro: Optional[str] = None
    # Indica si ya existe un vector (embedding) generado para esta persona
    tiene_embedding: bool = False
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True

class UpdPersonaAutorizada(BaseModel):
    """Campos editables para el perfil de una persona autorizada."""
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    id_cubiculo: Optional[int] = None
    rol: Optional[str] = None


# ─── Motor de reconocimiento ──────────────────────────────────────────────────

class ResultadoReconocimiento(BaseModel):
    """
    Respuesta inmediata tras el procesamiento de un frame de video.
    Cruza los datos del motor de IA con la identidad en la base de datos.
    """
    tipo_acceso: str # Ej: "Autorizado" o "No Autorizado"
    # Nivel de confianza (distancia euclidiana o similitud de coseno)
    similitud: float 
    id_persona: Optional[int] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # ID del evento generado para su posterior consulta o alerta
    id_evento: int


# ─── Bitacora de eventos ──────────────────────────────────────────────────────

class DatosEvento(BaseModel):
    """Representación de un registro histórico en la bitácora de accesos."""
    id_evento: int
    id_camara: Optional[int] = None
    id_persona: Optional[int] = None
    tipo_acceso: str
    fecha: Optional[date] = None
    hora: Optional[time] = None
    # Métrica de certeza con la que se registró el evento
    similitud: Optional[float] = None

    class Config:
        from_attributes = True