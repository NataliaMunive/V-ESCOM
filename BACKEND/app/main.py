
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import profesores, camaras, auth, reconocimiento

app = FastAPI(title="VESCOM API")

app.include_router(profesores.router)
app.include_router(camaras.router)
app.include_router(auth.router)
app.include_router(reconocimiento.router)

app = FastAPI(
    title="V-ESCOM API",
    description="Sistema de vigilancia con reconocimiento facial para cubículos ESCOM-IPN",
    version="1.0.0",
)

# CORS – ajusta los orígenes permitidos según tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # cambia a ["http://localhost:5173"] en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(reconocimiento.router)
app.include_router(profesores.router)
app.include_router(camaras.router)