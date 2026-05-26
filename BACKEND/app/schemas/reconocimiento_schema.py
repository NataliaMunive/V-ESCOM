"""
Esquemas de Validación (Pydantic) para Reconocimiento y Eventos - V-ESCOM

Define la estructura de los datos biométricos y el registro de acceso.
Maneja la información resultante de la comparación de rostros y la
trazabilidad de los eventos de seguridad detectados por las cámaras.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)

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


class ResultadoReconocimientoRostro(BaseModel):
    """Resultado individual al identificar una imagen con varios rostros."""
    indice_rostro: int
    bbox: Optional[list[int]] = None
    estado: str = "ok"
    detalle: Optional[str] = None
    tipo_acceso: Optional[str] = None
    similitud: Optional[float] = None
    id_persona: Optional[int] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    id_evento: Optional[int] = None


class ResultadoReconocimientoMultiples(BaseModel):
    """Respuesta agregada para múltiples rostros en una sola imagen."""
    total_detectados: int
    resultados: list[ResultadoReconocimientoRostro]


class ResultadoEntrenamiento(BaseModel):
    """Resumen de ejecución del entrenamiento del clasificador SVM."""
    personas_entrenadas: int
    total_embeddings: int
    accuracy: Optional[float] = None
    modelo_guardado_en: str
    mensaje: str


class ResultadoImagen(BaseModel):
    """Resultado individual de procesamiento para una imagen en carga múltiple."""
    nombre_archivo: str
    estado: str
    detalle: str
    similitud: Optional[float] = None


class ResultadoSubidaMultiple(BaseModel):
    """Respuesta agregada para registro de múltiples fotos de una persona."""
    id_persona: int
    total_recibidas: int
    exitosas: int
    fallidas: int
    resultados: list[ResultadoImagen]


# ─── Bitacora de eventos ──────────────────────────────────────────────────────

class DatosEvento(BaseModel):
    """Representación de un registro histórico en la bitácora de accesos."""
    model_config = ConfigDict(from_attributes=True)

    id_evento: int
    id_camara: Optional[int] = None
    id_persona: Optional[int] = None
    tipo_acceso: str
    fecha: Optional[date] = None
    hora: Optional[time] = None
    # Métrica de certeza con la que se registró el evento
    similitud: Optional[float] = None