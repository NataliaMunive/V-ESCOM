from fastapi import FastAPI
from app.routes import profesores

app = FastAPI(title="VESCOM API")

app.include_router(profesores.router)
