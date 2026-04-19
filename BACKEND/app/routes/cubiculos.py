from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.cubiculo import Cubiculo

router = APIRouter(prefix="/cubiculos", tags=["Cubículos"])

class CrearCubiculo(BaseModel):
    numero_cubiculo: str
    capacidad: int
    responsable: Optional[str] = None

class DatosCubiculo(BaseModel):
    id_cubiculo: int
    numero_cubiculo: str
    capacidad: int
    responsable: Optional[str] = None
    class Config:
        from_attributes = True

@router.get("/", response_model=List[DatosCubiculo])
def listar_cubiculos(
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    return db.query(Cubiculo).all()

@router.post("/", response_model=DatosCubiculo, status_code=201)
def crear_cubiculo(
    datos: CrearCubiculo,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    existente = db.query(Cubiculo).filter(
        Cubiculo.numero_cubiculo == datos.numero_cubiculo
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Número de cubículo ya registrado")
    nuevo = Cubiculo(**datos.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{id_cubiculo}", response_model=DatosCubiculo)
def actualizar_cubiculo(
    id_cubiculo: int,
    datos: CrearCubiculo,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    cubiculo = db.query(Cubiculo).filter(
        Cubiculo.id_cubiculo == id_cubiculo
    ).first()
    if not cubiculo:
        raise HTTPException(status_code=404, detail="Cubículo no encontrado")
    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(cubiculo, key, value)
    db.commit()
    db.refresh(cubiculo)
    return cubiculo

@router.delete("/{id_cubiculo}")
def eliminar_cubiculo(
    id_cubiculo: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    cubiculo = db.query(Cubiculo).filter(
        Cubiculo.id_cubiculo == id_cubiculo
    ).first()
    if not cubiculo:
        raise HTTPException(status_code=404, detail="Cubículo no encontrado")
    db.delete(cubiculo)
    db.commit()
    return {"message": "Cubículo eliminado correctamente"}