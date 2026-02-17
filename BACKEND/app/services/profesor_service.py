from sqlalchemy.orm import Session
from app.models.profesor import Profesor
from fastapi import HTTPException

def crear_profesor(db: Session, profesor_data):
    existente = db.query(Profesor).filter(
        Profesor.correo == profesor_data.correo
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="Correo ya registrado")

    nuevo_profesor = Profesor(
        nombre=profesor_data.nombre,
        correo=profesor_data.correo,
        id_cubiculo=profesor_data.id_cubiculo
    )

    db.add(nuevo_profesor)
    db.commit()
    db.refresh(nuevo_profesor)

    return nuevo_profesor


def obtener_profesores(db: Session):
    return db.query(Profesor).all()


def obtener_profesor(db: Session, id_profesor: int):
    profesor = db.query(Profesor).filter(
        Profesor.id_profesor == id_profesor
    ).first()

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    return profesor


def actualizar_profesor(db: Session, id_profesor: int, datos):
    profesor = obtener_profesor(db, id_profesor)

    for key, value in datos.dict(exclude_unset=True).items():
        setattr(profesor, key, value)

    db.commit()
    db.refresh(profesor)

    return profesor


def desactivar_profesor(db: Session, id_profesor: int):
    profesor = obtener_profesor(db, id_profesor)
    profesor.activo = False
    db.commit()
    return profesor
