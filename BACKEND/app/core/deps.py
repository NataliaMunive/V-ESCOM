"""
Dependencias de Seguridad - V-ESCOM

Este módulo define los mecanismos de inyección de dependencias para proteger
los endpoints de la API, asegurando que solo administradores legítimos y activos puedan realizar operaciones sensibles.

manejo de errores:
    - En login, si el correo no existe o la contraseña es incorrecta, se lanza HTTP 401 sin revelar cuál es el error específico (seguridad).
    - Si el token JWT es inválido o ha expirado, se lanza HTTP 401.
    - En decode_access_token, si el token no es válido, se retorna None para que la función de dependencia pueda manejarlo adecuadamente.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.security import decode_access_token
from app.models.administrador import Administrador

# Define el esquema de seguridad; FastAPI usará esta URL en el botón 'Authorize' de /docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Administrador:
    """
    Valida la identidad del administrador mediante el token de acceso.
    
    Proceso de validación:
    1. Verifica la integridad y vigencia del JWT.
    2. Extrae el identificador del administrador (sub).
    3. Confirma la existencia y el estado 'activo' en la base de datos.
    
    Raises:
        HTTP_401_UNAUTHORIZED: Si el token falla, el usuario no existe o está inactivo.
    """
    
    # Error genérico para no dar pistas sobre fallos de seguridad específicos
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el acceso. Inicie sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Intento de decodificación del JWT
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 2. Extracción del ID (Subject) del payload
    admin_id: str = payload.get("sub")
    if admin_id is None:
        raise credentials_exception

    # 3. Búsqueda en DB (solo admins activos)
    # Nota: Se agrupan validaciones para evitar el acceso a cuentas desactivadas
    admin = db.query(Administrador).filter(
        Administrador.id_admin == int(admin_id),
        Administrador.activo == True,
    ).first()

    if admin is None:
        raise credentials_exception

    return admin