"""
Router del módulo de reconocimiento facial.
Todas las rutas requieren autenticación JWT (admin).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.evento import EventoAcceso
from app.schemas.reconocimiento_schema import (
    CrearPersonaAutorizada,
    DatosEvento,
    DatosPersonaAutorizada,
    ResultadoReconocimiento,
    UpdPersonaAutorizada,
)
from app.services import reconocimiento_service

router = APIRouter(prefix="/reconocimiento", tags=["Reconocimiento Facial"])


# ─── CRUD Personas Autorizadas ────────────────────────────────────────────────

@router.post(
    "/personas",
    response_model=DatosPersonaAutorizada,
    status_code=201,
    summary="Registrar persona autorizada",
)
def crear_persona(
    datos: CrearPersonaAutorizada,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    return reconocimiento_service.crear_persona(db, datos)


@router.get(
    "/personas",
    response_model=List[DatosPersonaAutorizada],
    summary="Listar personas autorizadas",
)
def listar_personas(
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    personas = reconocimiento_service.obtener_personas(db)
    return [reconocimiento_service._a_schema(p) for p in personas]


@router.get(
    "/personas/{id_persona}",
    response_model=DatosPersonaAutorizada,
    summary="Obtener persona por ID",
)
def obtener_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    p = reconocimiento_service.obtener_persona(db, id_persona)
    return reconocimiento_service._a_schema(p)


@router.put(
    "/personas/{id_persona}",
    response_model=DatosPersonaAutorizada,
    summary="Actualizar persona autorizada",
)
def actualizar_persona(
    id_persona: int,
    datos: UpdPersonaAutorizada,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    p = reconocimiento_service.actualizar_persona(db, id_persona, datos)
    return reconocimiento_service._a_schema(p)


@router.delete(
    "/personas/{id_persona}",
    summary="Eliminar persona autorizada",
)
def eliminar_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    reconocimiento_service.eliminar_persona(db, id_persona)
    return {"message": "Persona eliminada correctamente"}


# ─── Gestión de rostros ───────────────────────────────────────────────────────

@router.post(
    "/personas/{id_persona}/rostro",
    response_model=DatosPersonaAutorizada,
    summary="Subir foto y generar embedding",
)
async def registrar_rostro(
    id_persona: int,
    imagen: UploadFile = File(..., description="Foto del rostro (JPEG/PNG, 1 sola cara)"),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    """
    Sube la imagen de referencia de una persona autorizada,
    extrae el embedding ArcFace y lo almacena en la BD.
    """
    return await reconocimiento_service.registrar_rostro(db, id_persona, imagen)


# ─── Identificación ───────────────────────────────────────────────────────────

@router.post(
    "/identificar",
    response_model=ResultadoReconocimiento,
    summary="Identificar rostro (autorizado / no autorizado)",
)
async def identificar(
    imagen: UploadFile = File(..., description="Frame capturado por la cámara"),
    id_camara: Optional[int] = Form(None, description="ID de la cámara que capturó el frame"),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    """
    Recibe un frame de cámara, extrae el embedding y lo compara
    con la base de datos. Registra el evento y retorna el resultado.
    """
    return await reconocimiento_service.identificar_rostro(db, imagen, id_camara)


# ─── Historial de eventos ─────────────────────────────────────────────────────

@router.get(
    "/eventos",
    response_model=List[DatosEvento],
    summary="Historial de eventos de acceso",
)
def listar_eventos(
    tipo: Optional[str] = Query(None, description="Filtrar: 'Autorizado' o 'No Autorizado'"),
    id_camara: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    query = db.query(EventoAcceso)
    if tipo:
        query = query.filter(EventoAcceso.tipo_acceso == tipo)
    if id_camara:
        query = query.filter(EventoAcceso.id_camara == id_camara)
    return query.order_by(EventoAcceso.id_evento.desc()).limit(limit).all()