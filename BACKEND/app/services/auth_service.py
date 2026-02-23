"""
Servicio de autenticación.
Reglas implementadas (doc §4.2.1):
  - Solo administradores pueden iniciar sesión.
  - 3 intentos fallidos → bloqueo de 5 minutos.
  - Contraseñas almacenadas como hash bcrypt.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.administrador import Administrador
from app.schemas.auth_schema import CrearAdmin, UpdAdmin

MAX_INTENTOS = 3
BLOQUEO_MINUTOS = 5


# ─── Login ────────────────────────────────────────────────────────────────────

def login(db: Session, email: str, contrasena: str) -> str:
    """
    Autentica un administrador.
    Retorna el JWT de acceso o lanza HTTPException.
    """
    admin = db.query(Administrador).filter(
        Administrador.email == email
    ).first()

    # No revelar si el correo existe o no (seguridad)
    if not admin:
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cuenta bloqueada. Intenta de nuevo en {segundos} segundos.",
            )
        else:
            # Bloqueo expirado, reiniciar contador
            admin.intentos_fallidos = 0
            admin.bloqueado_hasta = None

    if not admin.activo:
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
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Demasiados intentos fallidos. Cuenta bloqueada por {BLOQUEO_MINUTOS} minutos.",
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
    db.commit()

    token = create_access_token({"sub": str(admin.id_admin), "email": admin.email})
    return token


# ─── CRUD Administrador ───────────────────────────────────────────────────────

def crear_admin(db: Session, datos: CrearAdmin) -> Administrador:
    existente = db.query(Administrador).filter(
        Administrador.email == datos.email
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    nuevo = Administrador(
        nombre=datos.nombre,
        apellidos=datos.apellidos,
        email=datos.email,
        telefono=datos.telefono,
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