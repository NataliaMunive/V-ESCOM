"""
Punto de Entrada Principal - API V-ESCOM

Este módulo inicializa la aplicación FastAPI y configura los componentes centrales:
- Seguridad y Middleware (CORS).
- Inyección de rutas (Endpoints).
- Documentación automática de la vigilancia de cubículos.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pathlib import Path
from app.routes import profesores, camaras, auth, reconocimiento, alertas, ws_alertas, cubiculos
from app.routes import reportes
from app.routes import stream
from app.routes import rtsp as rtsp_routes
from app.services.rtsp_manager import rtsp_manager
from app.routes import capturas

# ─── Configuracion de la instancia ──────────────────────────────────────────────
app = FastAPI(
    title="V-ESCOM API",
    description="Sistema de vigilancia con reconocimiento facial para cubículos ESCOM-IPN",
    version="1.0.0",
)

# ─── MIDDLEWARE Y SEGURIDAD ─────────────────────────────────────────────────────
# Configuración de CORS para permitir la comunicación con el Frontend (React/Vue/etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # NOTA: En producción, reemplazar con el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registro de modulos) ─────────────────────────────────────────────
# Autenticación y gestión de sesiones
app.include_router(auth.router)

# Core: Lógica de procesamiento de imágenes y detección de rostros
app.include_router(reconocimiento.router)

# Gestión de recursos del sistema (CRUDs)
app.include_router(profesores.router)
app.include_router(camaras.router)
app.include_router(cubiculos.router)
app.include_router(alertas.router)
app.include_router(ws_alertas.router)
app.include_router(reportes.router)
app.include_router(stream.router)
app.include_router(rtsp_routes.router)
app.include_router(capturas.router)
rtsp_manager.inicializar(app)  

fotos_path = Path(__file__).resolve().parent.parent / "fotos_rostros"
app.mount("/fotos_rostros", StaticFiles(directory=str(fotos_path)), name="fotos_rostros")


def _traducir_error_validacion(error: dict) -> str:
    tipo = error.get("type", "")
    campo = " -> ".join(str(p) for p in error.get("loc", [])[1:])
    detalle = error.get("msg", "")
    contexto = error.get("ctx") or {}

    if tipo == "missing":
        return f"El campo {campo} es obligatorio"

    if tipo == "value_error" and "email address" in str(contexto.get("reason", detalle)).lower():
        return f"El campo {campo} debe ser un correo electrónico válido"

    if tipo.startswith("string_too_short"):
        return f"El campo {campo} es demasiado corto"

    if tipo.startswith("string_too_long"):
        return f"El campo {campo} es demasiado largo"

    if tipo.startswith("int_parsing") or tipo.startswith("int_type"):
        return f"El campo {campo} debe ser un número entero"

    if tipo.startswith("bool_parsing") or tipo.startswith("bool_type"):
        return f"El campo {campo} debe ser un valor booleano"

    if campo:
        return f"Error de validación en el campo {campo}"

    return "Error de validación en la solicitud"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores = [
        {
            **error,
            "msg": _traducir_error_validacion(error),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errores})

@app.get("/", tags=["Root"])
async def root():
    """Endpoint de salud para verificar que la API está operativa."""
    return {"status": "online", "system": "V-ESCOM"}