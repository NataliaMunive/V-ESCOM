"""
Servicio de Gestión de Cubículos - V-ESCOM

Provee un CRUD básico para los cubículos.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.cubiculo import Cubiculo

def crear_cubiculo(db: Session, cubiculo_data):
    nuevo_cubiculo = Cubiculo(
        numero_cubiculo=cubiculo_data.numero_cubiculo,
        capacidad=cubiculo_data.capacidad,
        responsable=cubiculo_data.responsable
    )
    db.add(nuevo_cubiculo)
    db.commit()
    db.refresh(nuevo_cubiculo)
    return nuevo_cubiculo

def obtener_cubiculos(db: Session):
    return db.query(Cubiculo).all()

def obtener_cubiculo(db: Session, id_cubiculo: int):
    cubiculo = db.query(Cubiculo).filter(Cubiculo.id_cubiculo == id_cubiculo).first()
    if not cubiculo:
        raise HTTPException(status_code=404, detail="Cubículo no encontrado")
    return cubiculo

def actualizar_cubiculo(db: Session, id_cubiculo: int, datos):
    cubiculo = obtener_cubiculo(db, id_cubiculo)
    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(cubiculo, key, value)
    db.commit()
    db.refresh(cubiculo)
    return cubiculo