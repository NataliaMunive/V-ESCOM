from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.bd import get_db
from app.schemas.profesor_schema import CrearProfesor, DatosProfesor, UpdProfesor
from app.services import profesor_service
from typing import List

router = APIRouter(prefix="/profesores", tags=["Profesores"])

@router.post("/", response_model=DatosProfesor)
def crear_profesor(profesor: CrearProfesor, db: Session = Depends(get_db)):
    return profesor_service.crear_profesor(db, profesor)

@router.get("/", response_model=List[DatosProfesor])
def listar_profesores(db: Session = Depends(get_db)):
    return profesor_service.obtener_profesores(db)


@router.get("/id_profesor", response_model=DatosProfesor)
def obtener_profesor(id_profesor: int, db: Session = Depends(get_db)):
    return profesor_service.obtener_profesor(db, id_profesor)


@router.put("/id_profesor", response_model=DatosProfesor)
def actualizar_profesor(id_profesor: int, datos: UpdProfesor, db: Session = Depends(get_db)):
    return profesor_service.actualizar_profesor(db, id_profesor, datos)


@router.delete("/id_profesor")
def desactivar_profesor(id_profesor: int, db: Session = Depends(get_db)):
    profesor_service.desactivar_profesor(db, id_profesor)
    return {"message": "Profesor desactivado correctamente"}
