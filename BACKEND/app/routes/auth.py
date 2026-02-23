from typing import List

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.schemas.auth_schema import (
    CrearAdmin,
    DatosAdmin,
    TokenResponse,
    UpdAdmin,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Autentica un administrador con email (username) y contraseña.
    Retorna un JWT Bearer válido por 60 minutos (configurable).
    """
    token = auth_service.login(db, form_data.username, form_data.password)
    return TokenResponse(access_token=token)


# ─── Administradores (rutas protegidas) ───────────────────────────────────────

@router.post(
    "/admins",
    response_model=DatosAdmin,
    status_code=201,
    summary="Registrar administrador",
)
def crear_admin(
    datos: CrearAdmin,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Solo un administrador autenticado puede crear otro administrador."""
    return auth_service.crear_admin(db, datos)


@router.get(
    "/admins",
    response_model=List[DatosAdmin],
    summary="Listar administradores",
)
def listar_admins(
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    return auth_service.obtener_admins(db)


@router.get(
    "/admins/me",
    response_model=DatosAdmin,
    summary="Perfil del administrador actual",
)
def perfil(current_admin: Administrador = Depends(get_current_admin)):
    return current_admin


@router.get(
    "/admins/{id_admin}",
    response_model=DatosAdmin,
    summary="Obtener administrador por ID",
)
def obtener_admin(
    id_admin: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    return auth_service.obtener_admin(db, id_admin)


@router.put(
    "/admins/{id_admin}",
    response_model=DatosAdmin,
    summary="Actualizar administrador",
)
def actualizar_admin(
    id_admin: int,
    datos: UpdAdmin,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    return auth_service.actualizar_admin(db, id_admin, datos)


@router.delete(
    "/admins/{id_admin}",
    summary="Desactivar administrador",
)
def desactivar_admin(
    id_admin: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    auth_service.desactivar_admin(db, id_admin)
    return {"message": "Administrador desactivado correctamente"}