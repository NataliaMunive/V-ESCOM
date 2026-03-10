"""
Router de Autenticación y Gestión de Administradores - V-ESCOM

Este módulo define los endpoints para el control de acceso y el CRUD de 
administradores. Utiliza OAuth2 con Password Flow y Tokens JWT.
"""

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

# Definición del router con prefijo global y etiquetas para Swagger
router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ─── Servicios de acceso (Publicos) ───────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Intercambia credenciales (email/contraseña) por un Token de Acceso.
    - **username**: Correo electrónico del administrador.
    - **password**: Contraseña en texto plano.
    """
    token = auth_service.login(db, form_data.username, form_data.password)
    return TokenResponse(access_token=token)


# ─── Gestion de administradores (Protegidos) ──────────────────────────────────
# Nota: Todos los endpoints siguientes requieren el Header 'Authorization: Bearer <token>'

@router.post(
    "/admins",
    response_model=DatosAdmin,
    status_code=201,
    summary="Registrar nuevo administrador",
)
def crear_admin(
    datos: CrearAdmin,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin), # Inyección de seguridad
):
    """Crea un nuevo usuario con privilegios de gestión en el sistema."""
    return auth_service.crear_admin(db, datos)


@router.get(
    "/admins",
    response_model=List[DatosAdmin],
    summary="Listar todos los administradores",
)
def listar_admins(
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Retorna la lista completa de administradores registrados (activos e inactivos)."""
    return auth_service.obtener_admins(db)


@router.get(
    "/admins/me",
    response_model=DatosAdmin,
    summary="Obtener perfil propio",
)
def perfil(current_admin: Administrador = Depends(get_current_admin)):
    """Retorna los datos del administrador asociado al token enviado."""
    return current_admin


@router.get(
    "/admins/{id_admin}",
    response_model=DatosAdmin,
    summary="Consultar administrador por ID",
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
    summary="Actualizar información de administrador",
)
def actualizar_admin(
    id_admin: int,
    datos: UpdAdmin,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Permite modificar nombres, correos o teléfonos de un administrador específico."""
    return auth_service.actualizar_admin(db, id_admin, datos)


@router.delete(
    "/admins/{id_admin}",
    summary="Desactivar cuenta de administrador",
)
def desactivar_admin(
    id_admin: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Realiza un 'Soft Delete' cambiando el estado del administrador a inactivo.
    No elimina el registro de la base de datos para preservar la integridad histórica.
    """
    auth_service.desactivar_admin(db, id_admin)
    return {"message": "Administrador desactivado correctamente"}