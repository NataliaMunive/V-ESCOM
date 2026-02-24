
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.camara import Camara


def crear_camara(db: Session, camara_data):

    nueva_camara = Camara(
        nombre=camara_data.nombre,
        direccion_ip=camara_data.direccion_ip,
        ubicacion=camara_data.ubicacion,
        id_cubiculo=camara_data.id_cubiculo,
        estado=camara_data.estado
    )

    db.add(nueva_camara)
    db.commit()
    db.refresh(nueva_camara)

    return nueva_camara


def obtener_camaras(db: Session):
    return db.query(Camara).all()


def obtener_camara(db: Session, id_camara: int):
    camara = db.query(Camara).filter(
        Camara.id_camara == id_camara
    ).first()

    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    return camara


def actualizar_camara(db: Session, id_camara: int, datos):
    camara = obtener_camara(db, id_camara)

    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(camara, key, value)

    db.commit()
    db.refresh(camara)

    return camara


def desactivar_camara(db: Session, id_camara: int):
    camara = obtener_camara(db, id_camara)
    camara.activa = False
    db.commit()
    return camara
