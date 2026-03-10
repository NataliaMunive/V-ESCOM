"""
Router de Gestión de Dispositivos (Camaras) - V-ESCOM

Define los endpoints para el inventario de hardware de videovigilancia.
Permite vincular cámaras físicas con cubículos específicos y gestionar su estado.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.bd import get_db
from app.schemas.camara_schema import CrearCamara, DatosCamara, UpdCamara
from app.services import camara_service
from app.core.deps import get_current_admin # Sugerencia: Proteger estas rutas
from app.models.administrador import Administrador

router = APIRouter(prefix="/camaras", tags=["Cámaras"])

# ─── OPERACIONES CRUD ─────────────────────────────────────────────────────────

@router.post("/", response_model=DatosCamara, status_code=201, summary="Registrar cámara")
def crear_camara(
    camara: CrearCamara, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Registra una nueva cámara en el sistema y la vincula a un cubículo."""
    return camara_service.crear_camara(db, camara)


@router.get("/", response_model=List[DatosCamara], summary="Listar todas las cámaras")
def listar_camaras(db: Session = Depends(get_db)):
    """Retorna el catálogo completo de cámaras registradas."""
    return camara_service.obtener_camaras(db)


@router.get("/{id_camara}", response_model=DatosCamara, summary="Obtener cámara por ID")
def obtener_camara(id_camara: int, db: Session = Depends(get_db)):
    """Consulta la configuración y estado de una cámara específica."""
    return camara_service.obtener_camara(db, id_camara)


@router.put("/{id_camara}", response_model=DatosCamara, summary="Actualizar cámara")
def actualizar_camara(
    id_camara: int, 
    datos: UpdCamara, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Modifica la IP, ubicación o estado de una cámara existente."""
    return camara_service.actualizar_camara(db, id_camara, datos)


@router.delete("/{id_camara}", summary="Desactivar cámara")
def desactivar_camara(
    id_camara: int, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """
    Cambia el estado de la cámara a 'Inactiva'. 
    Esto detiene el procesamiento de imágenes de este dispositivo en el motor de IA.
    """
    camara_service.desactivar_camara(db, id_camara)
    return {"message": "Cámara desactivada correctamente"}