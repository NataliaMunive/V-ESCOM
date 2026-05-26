from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.bd import get_db
from app.models.administrador import Administrador
from app.schemas.administrador_schema import AdministradorUpdate

router = APIRouter(prefix="/administradores", tags=["Administradores"])

@router.get("/")
def obtener_administradores(db: Session = Depends(get_db)):
    return db.query(Administrador).all()

@router.put("/{id_admin}")
def actualizar_administrador(id_admin: int, datos: AdministradorUpdate, db: Session = Depends(get_db)):
    db_admin = db.query(Administrador).filter(Administrador.id_admin == id_admin).first()
    
    if not db_admin:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")

    # Convertimos los datos a diccionario ignorando los campos vacíos
    update_data = datos.model_dump(exclude_unset=True)
    
    # Aplicamos los cambios al modelo
    for key, value in update_data.items():
        setattr(db_admin, key, value)
    
    db.commit()
    db.refresh(db_admin)
    return db_admin