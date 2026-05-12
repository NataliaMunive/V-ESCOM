"""
Pruebas Unitarias - Módulo 6.1: Autenticación y Control de Administradores
V-ESCOM

Casos cubiertos:
    VESCOM-AUTH-U01: Verificación de contraseña con BCrypt
    VESCOM-AUTH-U02: Generación y decodificación de JWT
    VESCOM-AUTH-U03: Token expirado retorna None
    VESCOM-AUTH-U07: Salt aleatoria en BCrypt

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_01/test_unitarias_auth.py -v
"""

import sys
import os
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# ── VESCOM-AUTH-U01 ───────────────────────────────────────────────────────────

def test_U01_verificar_contrasena_correcta():
    """Contraseña correcta debe retornar True."""
    hash_generado = hash_password("Admin1234!")
    resultado = verify_password("Admin1234!", hash_generado)
    assert resultado is True

def test_U01_verificar_contrasena_incorrecta():
    """Contraseña incorrecta debe retornar False."""
    hash_generado = hash_password("Admin1234!")
    resultado = verify_password("Incorrecta", hash_generado)
    assert resultado is False

# ── VESCOM-AUTH-U02 ───────────────────────────────────────────────────────────

def test_U02_token_contiene_sub_y_email():
    """El payload debe contener sub y email correctos."""
    token_generado = create_access_token({"sub": "1", "email": "admin@escom.mx"})
    datos_token = decode_access_token(token_generado)
    assert datos_token is not None
    assert datos_token["sub"] == "1"
    assert datos_token["email"] == "admin@escom.mx"

def test_U02_token_contiene_campo_expiracion():
    """El token debe incluir campo de expiración."""
    token_generado = create_access_token({"sub": "1"})
    datos_token = decode_access_token(token_generado)
    assert "exp" in datos_token

# ── VESCOM-AUTH-U03 ───────────────────────────────────────────────────────────

def test_U03_token_expirado_retorna_none():
    """Token con expiración negativa debe retornar None."""
    token_expirado = create_access_token(
        {"sub": "1"},
        expires_delta=timedelta(seconds=-1)
    )
    resultado = decode_access_token(token_expirado)
    assert resultado is None

# ── VESCOM-AUTH-U07 ───────────────────────────────────────────────────────────

def test_U07_hashes_distintos_misma_contrasena():
    """BCrypt debe generar hashes distintos para la misma contraseña (salt aleatoria)."""
    primer_hash = hash_password("Admin1234!")
    segundo_hash = hash_password("Admin1234!")
    assert primer_hash != segundo_hash

def test_U07_ambos_hashes_son_validos():
    """Ambos hashes distintos deben verificar la contraseña correctamente."""
    primer_hash = hash_password("Admin1234!")
    segundo_hash = hash_password("Admin1234!")
    primer_resultado = verify_password("Admin1234!", primer_hash)
    segundo_resultado = verify_password("Admin1234!", segundo_hash)
    assert primer_resultado is True
    assert segundo_resultado is True
