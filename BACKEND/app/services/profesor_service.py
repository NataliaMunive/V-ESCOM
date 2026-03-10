"""
Servicio de Gestion de Profesores (V-ESCOM).
Provee un CRUD para la administración de docentes autorizados en cubículos.

Campos clave:
    - id_profesor: Identificador único (PK).
    - nombre: Nombre completo.
    - correo: Email institucional (Único).
    - telefono: Número móvil en formato E.164 (Único, para alertas SMS).
    - id_cubiculo: Referencia al espacio asignado (FK).
    - activo: Estado del registro (Soft Delete).
Gestión de profesores:
    - Crear: Validación de correo y teléfono únicos. Normalización de teléfono MX.
    - Leer: Listar todos o por ID. Solo activos por defecto.
    - Actualizar: Permite modificar datos con validaciones de unicidad.
    - Eliminar: Soft delete (activo=False) para mantener historial.
Flujo de Notificaciones:
    - Se prioriza el envío de alertas vía SMS para eventos de acceso e intrusión.
    - El campo 'telefono' es obligatorio para profesores que recibirán notificaciones.
    - Validaciones estrictas para evitar duplicados en correo y teléfono.
Manejo de Errores:
    - En caso de conflicto, se devuelve un error 409 con mensaje claro.
    - Si el teléfono no es válido, se devuelve un error 422 indicando el formato esperado.
    - Si el profesor no existe, se devuelve un error 404.
"""""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.profesor import Profesor
from app.utils.phone_utils import normalizar_telefono_mx

# ─── CRUD Profesores ────────────────────────────────────────────────────────────────
# crear profesor
def crear_profesor(db: Session, profesor_data):
    telefono_norm = normalizar_telefono_mx(profesor_data.telefono)
    if not telefono_norm:
        raise HTTPException(status_code=422, detail="Teléfono inválido. Usa un número MX válido")
    # Validar unicidad de correo 
    existente = db.query(Profesor).filter(
        Profesor.correo == profesor_data.correo
    ).first()

    if existente:
        raise HTTPException(status_code=409, detail="Correo ya registrado")
    
    # Validar que el teléfono no esté registrado para otro profesor 
    telefono_existente = db.query(Profesor).filter(
        Profesor.telefono == telefono_norm
    ).first()

    if telefono_existente:
        raise HTTPException(status_code=409, detail="Teléfono ya registrado para notificaciones SMS")
# Si todo es válido, crear el nuevo profesor
    nuevo_profesor = Profesor(
        nombre=profesor_data.nombre,
        correo=profesor_data.correo,
        telefono=telefono_norm,
        id_cubiculo=profesor_data.id_cubiculo
    )

    db.add(nuevo_profesor)
    db.commit()
    db.refresh(nuevo_profesor)

    return nuevo_profesor

# Obtener todos los profesores o por ID
def obtener_profesores(db: Session):
    return db.query(Profesor).all()

# Obtener profesor por ID
def obtener_profesor(db: Session, id_profesor: int):
    profesor = db.query(Profesor).filter(
        Profesor.id_profesor == id_profesor
    ).first()

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    return profesor

# Actualizar profesor por ID
def actualizar_profesor(db: Session, id_profesor: int, datos):
    profesor = obtener_profesor(db, id_profesor)

    dict_datos = datos.model_dump(exclude_unset=True)

    if "correo" in dict_datos:
        correo_existente = db.query(Profesor).filter(
            Profesor.correo == dict_datos["correo"],
            Profesor.id_profesor != id_profesor,
        ).first()
        if correo_existente:
            raise HTTPException(status_code=409, detail="Correo ya registrado")

    if "telefono" in dict_datos:
        telefono_norm = normalizar_telefono_mx(dict_datos["telefono"])
        if not telefono_norm:
            raise HTTPException(status_code=422, detail="Teléfono inválido. Usa un número MX válido")

        telefono_existente = db.query(Profesor).filter(
            Profesor.telefono == telefono_norm,
            Profesor.id_profesor != id_profesor,
        ).first()

        if telefono_existente:
            raise HTTPException(status_code=409, detail="Teléfono ya registrado para notificaciones SMS")

        dict_datos["telefono"] = telefono_norm

    for key, value in dict_datos.items():
        setattr(profesor, key, value)

    db.commit()
    db.refresh(profesor)

    return profesor

# desactivar profesor por ID (Soft Delete)
def desactivar_profesor(db: Session, id_profesor: int):
    profesor = obtener_profesor(db, id_profesor)
    profesor.activo = False
    db.commit()
    return profesor
