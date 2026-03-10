"""
Utilidades para normalización de números telefónicos en formato E.164, enfocadas en México (+52).
Funciones:
    - normalizar_telefono_mx: Convierte diversos formatos de teléfono mexicano a E.164.
    - Retorna None para entradas vacías, nulas o no válidas.
Uso:
    normalizar_telefono_mx("55 1234 5678") -> "+525512345678"
    normalizar_telefono_mx("+52 1 55 1234 5678") -> "+525512345678"
    normalizar_telefono_mx("001 52 55 1234 5678") -> "+525512345678"
    normalizar_telefono_mx("12345") -> None
    normalizar_telefono_mx("") -> None
    normalizar_telefono_mx(None) -> None
Manejo de errores:
    - Si el número no tiene 10 dígitos (sin código de país) o no cumple con formatos reconocidos, se retorna None.
    - Solo se permiten números mexicanos (con o sin código +52).
    - Se eliminan caracteres no numéricos antes de la validación.

"""

import re

# ─── Reglas y Funciones ────────────────────────────────────────────────────────────────
def normalizar_telefono_mx(telefono: str | None) -> str | None:
    if not telefono:
        return None

    telefono = telefono.strip()
    if not telefono:
        return None

    solo_digitos = re.sub(r"\D", "", telefono)
    if not solo_digitos:
        return None

    if len(solo_digitos) == 10:
        return f"+52{solo_digitos}"

    if len(solo_digitos) == 12 and solo_digitos.startswith("52"):
        return f"+{solo_digitos}"

    if len(solo_digitos) == 13 and solo_digitos.startswith("521"):
        return f"+52{solo_digitos[3:]}"

    telefono_e164 = f"+{solo_digitos}"
    if re.fullmatch(r"\+[1-9]\d{7,14}", telefono_e164):
        return telefono_e164

    return None
