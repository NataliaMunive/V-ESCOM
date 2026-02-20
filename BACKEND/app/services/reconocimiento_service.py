"""
Servicio de reconocimiento facial.
Flujo:
  1. Registrar embedding de una persona autorizada (subiendo foto).
  2. Identificar un rostro contra la BD → retorna evento de acceso.

Umbral de similitud: 0.40 (configurable en .env como SIMILITUD_UMBRAL).
Con ArcFace normalizado, valores >0.4 indican la misma persona.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.evento import EventoAcceso, PersonaNoAutorizada
from app.models.persona_autorizada import PersonaAutorizada
from app.schemas.reconocimiento_schema import (
    CrearPersonaAutorizada,
    DatosPersonaAutorizada,
    ResultadoReconocimiento,
    UpdPersonaAutorizada,
)
from app.utils.face_utils import (
    bytes_a_embedding,
    embedding_a_bytes,
    extraer_embedding,
    similitud_coseno,
)

SIMILITUD_UMBRAL = float(os.getenv("SIMILITUD_UMBRAL", "0.40"))


# ─── CRUD Personas Autorizadas ────────────────────────────────────────────────

def crear_persona(db: Session, datos: CrearPersonaAutorizada) -> PersonaAutorizada:
    nueva = PersonaAutorizada(**datos.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


def obtener_personas(db: Session):
    return db.query(PersonaAutorizada).all()


def obtener_persona(db: Session, id_persona: int) -> PersonaAutorizada:
    p = db.query(PersonaAutorizada).filter(
        PersonaAutorizada.id_persona == id_persona
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return p


def actualizar_persona(
    db: Session, id_persona: int, datos: UpdPersonaAutorizada
) -> PersonaAutorizada:
    persona = obtener_persona(db, id_persona)
    for key, value in datos.model_dump(exclude_unset=True).items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return persona


def eliminar_persona(db: Session, id_persona: int) -> None:
    persona = obtener_persona(db, id_persona)
    db.delete(persona)
    db.commit()


# ─── Registro de rostro ───────────────────────────────────────────────────────

async def registrar_rostro(
    db: Session,
    id_persona: int,
    imagen: UploadFile,
    directorio_fotos: str = "fotos_rostros",
) -> DatosPersonaAutorizada:
    """
    Extrae el embedding de la imagen subida y lo guarda en la BD.
    También guarda la imagen en disco como referencia.
    """
    persona = obtener_persona(db, id_persona)

    contenido = await imagen.read()

    # Extraer embedding
    try:
        embedding = extraer_embedding(contenido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Guardar imagen en disco
    os.makedirs(directorio_fotos, exist_ok=True)
    nombre_archivo = f"{id_persona}_{imagen.filename}"
    ruta = os.path.join(directorio_fotos, nombre_archivo)
    with open(ruta, "wb") as f:
        f.write(contenido)

    # Persistir embedding y ruta
    persona.embedding = embedding_a_bytes(embedding)
    persona.ruta_rostro = ruta
    db.commit()
    db.refresh(persona)

    return _a_schema(persona)


# ─── Identificación ───────────────────────────────────────────────────────────

async def identificar_rostro(
    db: Session,
    imagen: UploadFile,
    id_camara: Optional[int] = None,
) -> ResultadoReconocimiento:
    """
    Compara el rostro de la imagen contra todos los embeddings registrados.
    Registra el evento en la BD y retorna el resultado.
    """
    contenido = await imagen.read()

    try:
        embedding_nuevo = extraer_embedding(contenido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Buscar la mejor coincidencia entre personas registradas
    personas = (
        db.query(PersonaAutorizada)
        .filter(PersonaAutorizada.embedding.isnot(None))
        .all()
    )

    mejor_similitud = -1.0
    mejor_persona: Optional[PersonaAutorizada] = None

    for p in personas:
        emb_registrado = bytes_a_embedding(p.embedding)
        sim = similitud_coseno(embedding_nuevo, emb_registrado)
        if sim > mejor_similitud:
            mejor_similitud = sim
            mejor_persona = p

    # Clasificar
    if mejor_persona and mejor_similitud >= SIMILITUD_UMBRAL:
        tipo_acceso = "Autorizado"
        id_persona = mejor_persona.id_persona
    else:
        tipo_acceso = "No Autorizado"
        id_persona = None

    # Guardar evento de acceso
    evento = EventoAcceso(
        id_camara=id_camara,
        id_persona=id_persona,
        tipo_acceso=tipo_acceso,
        similitud=round(mejor_similitud, 4),
    )
    db.add(evento)

    # Si no autorizado, guardar también en personas_no_autorizadas
    if tipo_acceso == "No Autorizado":
        pna = PersonaNoAutorizada(
            embedding_detectado=embedding_a_bytes(embedding_nuevo),
        )
        db.add(pna)

    db.commit()
    db.refresh(evento)

    return ResultadoReconocimiento(
        tipo_acceso=tipo_acceso,
        similitud=round(mejor_similitud, 4),
        id_persona=mejor_persona.id_persona if mejor_persona and tipo_acceso == "Autorizado" else None,
        nombre=mejor_persona.nombre if mejor_persona and tipo_acceso == "Autorizado" else None,
        apellidos=mejor_persona.apellidos if mejor_persona and tipo_acceso == "Autorizado" else None,
        id_evento=evento.id_evento,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _a_schema(persona: PersonaAutorizada) -> DatosPersonaAutorizada:
    return DatosPersonaAutorizada(
        id_persona=persona.id_persona,
        nombre=persona.nombre,
        apellidos=persona.apellidos,
        email=persona.email,
        telefono=persona.telefono,
        id_cubiculo=persona.id_cubiculo,
        rol=persona.rol,
        ruta_rostro=persona.ruta_rostro,
        tiene_embedding=persona.embedding is not None,
        fecha_registro=persona.fecha_registro,
    )