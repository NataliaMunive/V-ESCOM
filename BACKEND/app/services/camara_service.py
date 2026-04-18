"""
Servicio de Gestión de Cámaras (V-ESCOM).
Provee un CRUD para la administración de cámaras en cubículos.

Campos clave:
    - id_camara: Identificador único (PK).
    - nombre: Nombre descriptivo de la camara.
    - direccion_ip: IP de la camara para acceso y monitoreo.
    - ubicacion: Descripcion fisica de donde esta instalada.
    - id_cubiculo: Referencia al cubiculo asignado (FK).
    - estado: Estado operativo (activa/inactiva).
    
Gestion de camaras:
    - Crear: Permite registrar una nueva camara con validación de campos.
    - Leer: Listar todas o por ID. Solo activas por defecto.        
    - Actualizar: Permite modificar datos con validaciones basicas.
    - Desactivar: Cambia el estado a inactiva sin eliminar el registro (Soft Delete).

Manejo de Errores:
    - Si la camara no existe, se devuelve un error 404.
    - Validaciones básicas para campos requeridos y formato de IP.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.camara import Camara


def _normalizar_direccion_ip(direccion_ip):
    if direccion_ip is None:
        return None
    return str(direccion_ip)

# ─── CRUD Camaras ────────────────────────────────────────────────────────────────
def crear_camara(db: Session, camara_data):
    # crear camara con datos proporcionados
    nueva_camara = Camara(
        nombre=camara_data.nombre,
        direccion_ip=_normalizar_direccion_ip(camara_data.direccion_ip),
        ubicacion=camara_data.ubicacion,
        id_cubiculo=camara_data.id_cubiculo,
        estado=camara_data.estado
    )

    db.add(nueva_camara)
    db.commit()
    db.refresh(nueva_camara)

    return nueva_camara

# Obtener todas las camaras o por ID
def obtener_camaras(db: Session):
    return db.query(Camara).all()

# Obtener camara por ID
def obtener_camara(db: Session, id_camara: int):
    camara = db.query(Camara).filter(
        Camara.id_camara == id_camara
    ).first()

    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    return camara

# Actualizar camara por ID
def actualizar_camara(db: Session, id_camara: int, datos):
    camara = obtener_camara(db, id_camara)

    update_data = datos.model_dump(exclude_unset=True)
    if "direccion_ip" in update_data:
        update_data["direccion_ip"] = _normalizar_direccion_ip(update_data["direccion_ip"])

    for key, value in update_data.items():
        setattr(camara, key, value)

    db.commit()
    db.refresh(camara)

    return camara

# Desactivar camara por ID (Soft Delete)
def desactivar_camara(db: Session, id_camara: int):
    camara = obtener_camara(db, id_camara)
    camara.activa = False
    db.commit()
    return camara
