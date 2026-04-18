"""
Router de Gestión de Cubículos - V-ESCOM

Define los endpoints para el inventario de cubículos.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.bd import get_db
from app.schemas.cubiculo_schema import CrearCubiculo, DatosCubiculo, UpdCubiculo
from app.services import cubiculo_service
from app.core.deps import get_current_admin
from app.models.administrador import Administrador

router = APIRouter(prefix="/cubiculos", tags=["Cubículos"])

@router.post("/", response_model=DatosCubiculo, status_code=201, summary="Registrar cubículo")
def crear_cubiculo(
    cubiculo: CrearCubiculo, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Registra un nuevo cubículo en el sistema."""
    return cubiculo_service.crear_cubiculo(db, cubiculo)

@router.get("/", response_model=List[DatosCubiculo], summary="Listar todos los cubículos")
def listar_cubiculos(db: Session = Depends(get_db)):
    """Retorna el catálogo completo de cubículos registrados."""
    return cubiculo_service.obtener_cubiculos(db)

@router.get("/{id_cubiculo}", response_model=DatosCubiculo, summary="Obtener cubículo por ID")
def obtener_cubiculo(id_cubiculo: int, db: Session = Depends(get_db)):
    """Consulta la configuración de un cubículo específico."""
    return cubiculo_service.obtener_cubiculo(db, id_cubiculo)

@router.put("/{id_cubiculo}", response_model=DatosCubiculo, summary="Actualizar cubículo")
def actualizar_cubiculo(
    id_cubiculo: int, 
    datos: UpdCubiculo, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Actualiza los datos de un cubículo."""
    return cubiculo_service.actualizar_cubiculo(db, id_cubiculo, datos)

@router.delete("/{id_cubiculo}", summary="Eliminar cubículo")
def eliminar_cubiculo(
    id_cubiculo: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Elimina un cubículo si no tiene relaciones activas."""
    cubiculo_service.eliminar_cubiculo(db, id_cubiculo)
    return {"message": "Cubículo eliminado correctamente"}