"""
Esquemas de Validación (Pydantic) para Alertas - V-ESCOM

Define la estructura de datos para la visualización y gestión de incidencias.
El esquema de salida consolida información del evento original para facilitar
la interpretación del administrador.
"""

from datetime import date, time
from typing import Literal, Optional
from pydantic import BaseModel, Field

# ─── Esquemas de alerta ───────────────────────────────────────────────────────

class DatosAlerta(BaseModel):
    """
    Vista detallada de una alerta. 
    Incluye datos denormalizados del evento para evitar múltiples consultas.
    """
    id_alerta: int
    id_evento: int
    
    # Información de clasificación
    tipo_alerta: str = Field(..., example="Intrusion")
    estado: str = Field(..., example="Pendiente")
    
    # Datos provenientes de la relación con el Evento
    tipo_acceso: Optional[str] = Field(None, description="'Autorizado' o 'No Autorizado'")
    id_camara: Optional[int] = None
    similitud: Optional[float] = Field(None, description="Confianza del reconocimiento facial")
    
    # Estampas de tiempo del suceso
    fecha: Optional[date] = None
    hora: Optional[time] = None

    class Config:
        # Habilita la lectura de objetos ORM con relaciones cargadas (eager loading)
        from_attributes = True


class UpdAlerta(BaseModel):
    """
    Esquema para la actualización de estados de una alerta.
    Restringe los estados a valores válidos para el flujo de trabajo.
    """
    # asegura que solo se acepten estos dos strings específicos
    estado: Optional[Literal["Pendiente", "Notificada"]] = None
    tipo_alerta: Optional[str] = None