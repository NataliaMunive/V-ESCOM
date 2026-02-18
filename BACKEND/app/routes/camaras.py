from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.bd import get_db
from app.schemas.camara_schema import CrearCamara, DatosCamara, UpdCamara
from app.services import camara_service

router = APIRouter(prefix="/camaras", tags=["Cámaras"])

@router.post("/", response_model=DatosCamara)
def crear_camara(camara: CrearCamara, db: Session = Depends(get_db)):
    return camara_service.crear_camara(db, camara)


@router.get("/", response_model=List[DatosCamara])
def listar_camaras(db: Session = Depends(get_db)):
    return camara_service.obtener_camaras(db)


@router.get("/id_camara", response_model=DatosCamara)
def obtener_camara(id_camara: int, db: Session = Depends(get_db)):
    return camara_service.obtener_camara(db, id_camara)


@router.put("/id_camara", response_model=DatosCamara)
def actualizar_camara(id_camara: int, datos: UpdCamara, db: Session = Depends(get_db)):
    return camara_service.actualizar_camara(db, id_camara, datos)


@router.delete("/id_camara")
def desactivar_camara(id_camara: int, db: Session = Depends(get_db)):
    camara_service.desactivar_camara(db, id_camara)
    return {"message": "Cámara desactivada correctamente"}
