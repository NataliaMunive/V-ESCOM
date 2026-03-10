"""
Router de Gestión de Profesores - V-ESCOM

Maneja el catálogo de docentes responsables de los cubículos. 
Estos registros son la base para el envío de notificaciones de acceso 
y alertas de seguridad específicas por ubicación.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.schemas.profesor_schema import CrearProfesor, DatosProfesor, UpdProfesor
from app.services import profesor_service

router = APIRouter(prefix="/profesores", tags=["Profesores"])

# ─── Operaciones de administracion ────────────────────────────────────────────

@router.post("/", response_model=DatosProfesor, status_code=201, summary="Registrar profesor")
def crear_profesor(
    profesor: CrearProfesor, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """
    Registra un nuevo profesor y lo vincula a un cubículo.
    Requiere autenticación de administrador.
    """
    return profesor_service.crear_profesor(db, profesor)


@router.get("/", response_model=List[DatosProfesor], summary="Listar todos los profesores")
def listar_profesores(
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Retorna la lista de docentes registrados en el sistema de vigilancia."""
    return profesor_service.obtener_profesores(db)


@router.get("/{id_profesor}", response_model=DatosProfesor, summary="Consultar profesor por ID")
def obtener_profesor(
    id_profesor: int, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Obtiene los detalles de contacto y adscripción de un profesor específico."""
    return profesor_service.obtener_profesor(db, id_profesor)


@router.put("/{id_profesor}", response_model=DatosProfesor, summary="Actualizar datos de profesor")
def actualizar_profesor(
    id_profesor: int, 
    datos: UpdProfesor, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """Permite modificar el teléfono, correo o cubículo asignado al docente."""
    return profesor_service.actualizar_profesor(db, id_profesor, datos)


@router.delete("/{id_profesor}", summary="Dar de baja profesor")
def desactivar_profesor(
    id_profesor: int, 
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin)
):
    """
    Realiza una baja lógica (Soft Delete). 
    El profesor dejará de recibir notificaciones de seguridad.
    """
    profesor_service.desactivar_profesor(db, id_profesor)
    return {"message": "Profesor desactivado correctamente"}