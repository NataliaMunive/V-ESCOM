from fastapi import FastAPI
from app.routes import profesores, camaras

app = FastAPI(title="VESCOM API")

app.include_router(profesores.router)
app.include_router(camaras.router)

