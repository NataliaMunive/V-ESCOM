"""
Router de Gestión de Alertas de Seguridad - V-ESCOM

Define los puntos de acceso para la monitorización y resolución de incidencias.
Permite filtrar el historial de alertas por estado, tipo y origen del evento.
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.schemas.alerta_schema import DatosAlerta, UpdAlerta
from app.services import alerta_service

router = APIRouter(prefix="/alertas", tags=["Alertas"])

# ─── Consulta de incidencias ──────────────────────────────────────────────────

@router.get("/", response_model=List[DatosAlerta], summary="Listar alertas filtradas")
def listar_alertas(
    # Filtros de búsqueda para facilitar la auditoría
    estado: str | None = Query(default=None, description="Filtrar por 'Pendiente' o 'Notificada'"),
    tipo_alerta: str | None = Query(default=None, description="Filtrar por el tipo de alerta"),
    tipo_acceso: str | None = Query(default=None, description="Filtrar por acceso 'Autorizado' o 'No Autorizado'"),
    
    # Parámetros de paginación para optimizar el rendimiento
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin), # Ruta protegida
):
    """
    Obtiene el historial de alertas del sistema.
    Permite realizar búsquedas específicas y navegar mediante paginación.
    """
    return alerta_service.obtener_alertas(
        db,
        estado=estado,
        tipo_alerta=tipo_alerta,
        tipo_acceso=tipo_acceso,
        limit=limit,
        offset=offset,
    )


# ─── Resolucion de alertas ───────────────────────────────────────────────────

@router.put("/{id_alerta}", response_model=DatosAlerta, summary="Actualizar estado de alerta")
def actualizar_alerta(
    id_alerta: int,
    datos: UpdAlerta,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Permite modificar manualmente el estado de una alerta.
    Útil para marcar alertas como 'Revisadas' o 'Resueltas' por el administrador.
    """
    return alerta_service.actualizar_alerta(db, id_alerta, datos)