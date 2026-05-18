"""
Servicio de autenticación.

Reglas implementadas (doc §4.2.1):
  - Solo administradores pueden iniciar sesión.
  - 3 intentos fallidos → bloqueo de 5 minutos.
  - Contraseñas almacenadas como hash bcrypt.
Funciones:
    - login: Autentica y retorna JWT. Maneja bloqueos e intentos.
    - CRUD Administrador: Crear, leer, actualizar (incluye contraseña), desactivar.
Manejo de errores:
    - 401 para credenciales incorrectas.
    - 403 para cuenta bloqueada o desactivada.
    - 404 para administrador no encontrado.
    - 409 para correo ya registrado en creación/actualización.
    - 422 para formato de teléfono inválido.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.administrador import Administrador
from app.schemas.auth_schema import CrearAdmin, UpdAdmin
from app.services.log_sistema_service import registrar_log
from app.utils.phone_utils import normalizar_telefono_mx

MAX_INTENTOS = 3
BLOQUEO_MINUTOS = 5


def _normalizar_email(email: str | None) -> str | None:
    if email is None:
        return None
    email = email.strip().lower()
    return email or None


def _normalizar_telefono(telefono: str | None) -> str | None:
    return normalizar_telefono_mx(telefono)


def _buscar_conflicto_admin(
    db: Session,
    *,
    email: str | None,
    telefono: str | None,
    excluir_id_admin: int | None = None,
) -> tuple[str | None, Administrador | None]:
    query = db.query(Administrador)
    if excluir_id_admin is not None:
        query = query.filter(Administrador.id_admin != excluir_id_admin)

    for admin in query.all():
        email_admin = _normalizar_email(admin.email)
        if email and email_admin == email:
            return "correo", admin

        if telefono and _normalizar_telefono(admin.telefono) == telefono:
            return "telefono", admin

    return None, None


# ─── Login ────────────────────────────────────────────────────────────────────

def login(db: Session, email: str, contrasena: str) -> str:
    """
    Autentica un administrador.
    Retorna el JWT de acceso o lanza HTTPException.
    """
    email_norm = _normalizar_email(email)
    admin = db.query(Administrador).filter(
        func.lower(Administrador.email) == email_norm
    ).first()

    # No revelar si el correo existe o no (seguridad)
    if not admin:
        registrar_log(
            db,
            nivel="WARNING",
            origen="Auth_Service",
            tipo="Autenticacion",
            mensaje=f"Intento de login con correo no registrado: {email}",
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    # Verificar bloqueo temporal
    now = datetime.now(timezone.utc)
    if admin.bloqueado_hasta:
        bloqueado_hasta = admin.bloqueado_hasta
        # Hacer timezone-aware si viene sin tz de la BD
        if bloqueado_hasta.tzinfo is None:
            bloqueado_hasta = bloqueado_hasta.replace(tzinfo=timezone.utc)
        if now < bloqueado_hasta:
            segundos = int((bloqueado_hasta - now).total_seconds())
            registrar_log(
                db,
                nivel="WARNING",
                origen="Auth_Service",
                tipo="Autenticacion",
                mensaje=(
                    f"Login rechazado por bloqueo temporal para admin #{admin.id_admin}. "
                    f"Segundos restantes: {segundos}"
                ),
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cuenta bloqueada. Intenta de nuevo en {segundos} segundos.",
            )
        else:
            # Bloqueo expirado, reiniciar contador
            admin.intentos_fallidos = 0
            admin.bloqueado_hasta = None

    if not admin.activo:
        registrar_log(
            db,
            nivel="WARNING",
            origen="Auth_Service",
            tipo="Autenticacion",
            mensaje=f"Login rechazado para admin inactivo #{admin.id_admin}",
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )

    # Verificar contraseña
    if not verify_password(contrasena, admin.contrasena):
        admin.intentos_fallidos = (admin.intentos_fallidos or 0) + 1
        if admin.intentos_fallidos >= MAX_INTENTOS:
            admin.bloqueado_hasta = now + timedelta(minutes=BLOQUEO_MINUTOS)
            admin.intentos_fallidos = 0
            registrar_log(
                db,
                nivel="WARNING",
                origen="Auth_Service",
                tipo="Autenticacion",
                mensaje=(
                    f"Bloqueo temporal aplicado a admin #{admin.id_admin} "
                    f"por exceder intentos fallidos"
                ),
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Demasiados intentos fallidos. Cuenta bloqueada por {BLOQUEO_MINUTOS} minutos.",
            )
        registrar_log(
            db,
            nivel="WARNING",
            origen="Auth_Service",
            tipo="Autenticacion",
            mensaje=f"Credenciales invalidas para admin #{admin.id_admin}",
        )
        db.commit()
        restantes = MAX_INTENTOS - admin.intentos_fallidos
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Credenciales incorrectas. Intentos restantes: {restantes}",
        )

    # Login exitoso → reiniciar contadores
    admin.intentos_fallidos = 0
    admin.bloqueado_hasta = None
    registrar_log(
        db,
        nivel="INFO",
        origen="Auth_Service",
        tipo="Autenticacion",
        mensaje=f"Inicio de sesion exitoso para admin #{admin.id_admin}",
    )
    db.commit()

    token = create_access_token({"sub": str(admin.id_admin), "email": admin.email})
    return token


# ─── CRUD Administrador ───────────────────────────────────────────────────────

def crear_admin(db: Session, datos: CrearAdmin) -> Administrador:
    email_norm = _normalizar_email(datos.email)
    telefono_norm = _normalizar_telefono(datos.telefono)

    if datos.telefono and telefono_norm is None:
        raise HTTPException(status_code=422, detail="El teléfono no es válido")

    conflicto, _ = _buscar_conflicto_admin(
        db,
        email=email_norm,
        telefono=telefono_norm,
    )
    if conflicto == "correo":
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    if conflicto == "telefono":
        raise HTTPException(status_code=409, detail="El teléfono ya está registrado")

    nuevo = Administrador(
        nombre=datos.nombre,
        apellidos=datos.apellidos,
        email=email_norm,
        telefono=telefono_norm,
        contrasena=hash_password(datos.contrasena),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def obtener_admin(db: Session, id_admin: int) -> Administrador:
    admin = db.query(Administrador).filter(
        Administrador.id_admin == id_admin
    ).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    return admin


def obtener_admins(db: Session):
    return db.query(Administrador).all()


def actualizar_admin(db: Session, id_admin: int, datos: UpdAdmin) -> Administrador:
    admin = obtener_admin(db, id_admin)
    update_data = datos.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        update_data["email"] = _normalizar_email(update_data["email"])

    if "telefono" in update_data:
        telefono_norm = _normalizar_telefono(update_data["telefono"])
        if update_data["telefono"] and telefono_norm is None:
            raise HTTPException(status_code=422, detail="El teléfono no es válido")
        update_data["telefono"] = telefono_norm

    conflicto, _ = _buscar_conflicto_admin(
        db,
        email=update_data.get("email"),
        telefono=update_data.get("telefono"),
        excluir_id_admin=id_admin,
    )
    if conflicto == "correo":
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    if conflicto == "telefono":
        raise HTTPException(status_code=409, detail="El teléfono ya está registrado")

    if "contrasena" in update_data:
        update_data["contrasena"] = hash_password(update_data["contrasena"])
    for key, value in update_data.items():
        setattr(admin, key, value)
    db.commit()
    db.refresh(admin)
    return admin


def desactivar_admin(db: Session, id_admin: int) -> None:
    admin = obtener_admin(db, id_admin)
    admin.activo = False
    db.commit()