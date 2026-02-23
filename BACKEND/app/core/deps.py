"""
Dependencias de autenticación para inyectar en los routers de FastAPI.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.security import decode_access_token
from app.models.administrador import Administrador

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Administrador:
    """
    Dependencia que extrae y valida el JWT.
    Inyectar en cualquier endpoint protegido:
        admin = Depends(get_current_admin)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    admin_id: int = payload.get("sub")
    if admin_id is None:
        raise credentials_exception

    admin = db.query(Administrador).filter(
        Administrador.id_admin == int(admin_id),
        Administrador.activo == True,
    ).first()

    if admin is None:
        raise credentials_exception

    return admin