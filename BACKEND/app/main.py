"""
Punto de Entrada Principal - API V-ESCOM

Este módulo inicializa la aplicación FastAPI y configura los componentes centrales:
- Seguridad y Middleware (CORS).
- Inyección de rutas (Endpoints).
- Documentación automática de la vigilancia de cubículos.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import profesores, camaras, auth, reconocimiento

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

@app.get("/", tags=["Root"])
async def root():
    """Endpoint de salud para verificar que la API está operativa."""
    return {"status": "online", "system": "V-ESCOM"}