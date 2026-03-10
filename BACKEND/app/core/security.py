"""
Módulo de Seguridad y Autenticación - V-ESCOM

Responsabilidades:
1. Criptografía: Hashing de contraseñas mediante el algoritmo robusto BCrypt.
2. Identidad: Generación y validación de JSON Web Tokens (JWT) para sesiones.
3. Protección: Implementación de políticas de error opacas para prevenir enumeración de usuarios.

Manejo de errores:
    - En login, si el correo no existe o la contraseña es incorrecta, se lanza HTTP 401 sin revelar cuál es el error específico.
    - Si el token JWT es inválido o ha expirado, se lanza HTTP 401.
    - En decode_access_token, si el token no es válido, se retorna None para que la función de dependencia pueda manejarlo adecuadamente.

"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ─── Configuración de seguridad ───────────────────────────────────────────────
# Se recomienda usar una clave de al menos 32 caracteres aleatorios en el .env
SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Contexto para el manejo de contraseñas (BCrypt maneja automáticamente el salt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── Gestion de credenciales ──────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Transforma una contraseña en texto plano a un hash seguro e irreversible."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Compara una contraseña candidata contra el hash almacenado en la DB."""
    return pwd_context.verify(plain, hashed)

# ─── Gestion de tokens (JWT) ──────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token firmado que encapsula la identidad del usuario y su expiración.
    
    Args:
        data: Diccionario con los claims (ej. {'sub': 'email@ipn.mx'}).
        expires_delta: Tiempo de vida opcional, por defecto usa ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """
    Verifica la integridad y vigencia de un token.
    
    Retorna:
        dict: El contenido del token si es válido.
        None: Si el token está expirado, mal formado o la firma no coincide.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None