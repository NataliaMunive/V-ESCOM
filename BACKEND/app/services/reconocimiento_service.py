"""
Servicio de reconocimiento facial.
Flujo:
  1. Registrar embedding de una persona autorizada (subiendo foto).
  2. Identificar un rostro contra la BD → retorna evento de acceso.

Umbral de similitud: 0.40 (configurable en .env como SIMILITUD_UMBRAL).
Con ArcFace normalizado, valores >0.4 indican la misma persona.

Manejo de eventos:
    - Si no autorizado, se registra en EventoAcceso y PersonaNoAutorizada.
    - Se envía notificación de intrusión a administradores activos con teléfono registrado.

Manejo de errores:
    - 404 si la persona no existe al registrar rostro.
    - 422 para errores en extracción de embedding (ej. imagen sin rostro).
    - En caso de error en notificación, se registra el evento pero se omite el envío de SMS.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.evento import EventoAcceso, PersonaNoAutorizada
from app.models.persona_autorizada import PersonaAutorizada
from app.models.profesor import Profesor
from app.models.rostro_autorizado import RostroAutorizado
from app.schemas.reconocimiento_schema import (
    CrearPersonaAutorizada,
    DatosPersonaAutorizada,
    ResultadoReconocimiento,
    UpdPersonaAutorizada,
)
from app.services import notificacion_service
from app.services.log_sistema_service import registrar_log
from app.services.websocket_manager import alertas_ws_manager
from app.utils.face_utils import extraer_embedding
from app.utils.phone_utils import normalizar_telefono_mx

SIMILITUD_UMBRAL = float(os.getenv("SIMILITUD_UMBRAL", "0.40"))


def _nombre_completo(persona: PersonaAutorizada) -> str:
    return f"{persona.nombre} {persona.apellidos or ''}".strip()


def _buscar_profesor_sincronizado(
    db: Session,
    *,
    correo: str | None = None,
    telefono: str | None = None,
) -> Profesor | None:
    query = db.query(Profesor)
    if correo:
        profesor = query.filter(Profesor.correo == correo).first()
        if profesor is not None:
            return profesor
    if telefono:
        telefono_norm = normalizar_telefono_mx(telefono)
        if telefono_norm:
            profesor = query.filter(Profesor.telefono == telefono_norm).first()
            if profesor is not None:
                return profesor
    return None


def _sincronizar_profesor_desde_persona(db: Session, persona: PersonaAutorizada) -> None:
    if (persona.rol or '').strip().lower() != 'profesor':
        return

    correo = (persona.email or '').strip() or None
    telefono = normalizar_telefono_mx(persona.telefono)
    profesor = _buscar_profesor_sincronizado(db, correo=correo, telefono=telefono)

    if profesor is None:
        if correo is None:
            return
        profesor = Profesor(
            nombre=_nombre_completo(persona),
            correo=correo,
            telefono=telefono,
            id_cubiculo=persona.id_cubiculo,
            activo=True,
        )
        db.add(profesor)
        return

    profesor.nombre = _nombre_completo(persona)
    if correo is not None:
        profesor.correo = correo
    if telefono is not None:
        profesor.telefono = telefono
    profesor.id_cubiculo = persona.id_cubiculo
    profesor.activo = True


def _desactivar_profesor_sincronizado(db: Session, persona: PersonaAutorizada) -> None:
    profesor = _buscar_profesor_sincronizado(
        db,
        correo=persona.email,
        telefono=persona.telefono,
    )
    if profesor is not None:
        profesor.activo = False


def _buscar_persona_profesor_sincronizada(
    db: Session,
    *,
    correo: str | None = None,
    telefono: str | None = None,
) -> PersonaAutorizada | None:
    query = db.query(PersonaAutorizada).filter(PersonaAutorizada.rol == 'Profesor')
    if correo:
        persona = query.filter(PersonaAutorizada.email == correo).first()
        if persona is not None:
            return persona
    if telefono:
        telefono_norm = normalizar_telefono_mx(telefono)
        if telefono_norm:
            persona = query.filter(PersonaAutorizada.telefono == telefono_norm).first()
            if persona is not None:
                return persona
    return None

# ─── CRUD Personas Autorizadas ────────────────────────────────────────────────

def crear_persona(db: Session, datos: CrearPersonaAutorizada) -> PersonaAutorizada:
    datos_dict = datos.model_dump()
    # Normalizar email y telefono para evitar discrepancias de formato
    if datos_dict.get('email'):
        datos_dict['email'] = datos_dict['email'].strip().lower()
    if datos_dict.get('telefono'):
        datos_dict['telefono'] = normalizar_telefono_mx(datos_dict['telefono'])
    if (datos_dict.get('rol') or '').strip().lower() == 'profesor':
        existente = _buscar_persona_profesor_sincronizada(
            db,
            correo=datos_dict.get('email'),
            telefono=datos_dict.get('telefono'),
        )
        if existente is not None:
            for key, value in datos_dict.items():
                setattr(existente, key, value)
            db.commit()
            db.refresh(existente)
            _sincronizar_profesor_desde_persona(db, existente)
            db.commit()
            return existente

    nueva = PersonaAutorizada(**datos_dict)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    _sincronizar_profesor_desde_persona(db, nueva)
    db.commit()
    return nueva

# Obtener todas las personas autorizadas o por ID
def obtener_personas(db: Session):
    return db.query(PersonaAutorizada).all()

# Obtener persona autorizada por ID
def obtener_persona(db: Session, id_persona: int) -> PersonaAutorizada:
    p = db.query(PersonaAutorizada).filter(
        PersonaAutorizada.id_persona == id_persona
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return p

# Actualizar persona autorizada por ID
def actualizar_persona(
    db: Session, id_persona: int, datos: UpdPersonaAutorizada
) -> PersonaAutorizada:
    persona = obtener_persona(db, id_persona)
    rol_anterior = (persona.rol or '').strip().lower()
    updates = datos.model_dump(exclude_unset=True)
    if updates.get('email'):
        updates['email'] = updates['email'].strip().lower()
    if updates.get('telefono'):
        updates['telefono'] = normalizar_telefono_mx(updates['telefono'])
    for key, value in updates.items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    rol_actual = (persona.rol or '').strip().lower()
    if rol_actual == 'profesor':
        _sincronizar_profesor_desde_persona(db, persona)
    elif rol_anterior == 'profesor' and rol_actual != 'profesor':
        _desactivar_profesor_sincronizado(db, persona)
    db.commit()
    return persona

# Eliminar persona autorizada por ID (borrado físico)
def eliminar_persona(db: Session, id_persona: int) -> None:
    persona = obtener_persona(db, id_persona)
    _desactivar_profesor_sincronizado(db, persona)
    db.delete(persona)
    db.commit()


# ─── Registro de rostro ───────────────────────────────────────────────────────
async def registrar_rostro(
    db: Session,
    id_persona: int,
    imagen: UploadFile,
    directorio_fotos: str = "fotos_rostros",
    forzar: bool = False,          
) -> DatosPersonaAutorizada:
    """
    Extrae el embedding de la imagen subida y lo guarda en la BD.
    Antes de persistir, verifica que no exista un rostro similar registrado
    para otra persona (duplicado). Si hay coincidencia y forzar=False,
    lanza HTTP 409 con los datos del posible duplicado.
    """
    persona = obtener_persona(db, id_persona)
    contenido = await imagen.read()
 
    # Extraer embedding
    try:
        embedding = extraer_embedding(contenido)
    except ValueError as e:
        registrar_log(
            db,
            nivel="WARNING",
            origen="Motor_IA",
            tipo="Reconocimiento",
            mensaje=f"Error al extraer embedding para persona #{id_persona}: {e}",
            commit=True,
        )
        raise HTTPException(status_code=422, detail=str(e))
 
    if not forzar:
        UMBRAL_DUPLICADO = float(os.getenv("SIMILITUD_UMBRAL", "0.40"))
        distancia = RostroAutorizado.embedding.cosine_distance(embedding.tolist())
        duplicado = (
            db.query(RostroAutorizado, PersonaAutorizada, distancia.label("distancia"))
            .join(
                PersonaAutorizada,
                PersonaAutorizada.id_persona == RostroAutorizado.id_persona,
            )
            .filter(
                RostroAutorizado.embedding.isnot(None),
                RostroAutorizado.id_persona != id_persona,
            )
            .order_by(distancia)
            .first()
        )

        if duplicado:
            _, p_existente, distancia_duplicado = duplicado
            sim = 1.0 - float(distancia_duplicado)
            if sim >= UMBRAL_DUPLICADO:
                registrar_log(
                    db,
                    nivel="WARNING",
                    origen="Motor_IA",
                    tipo="Reconocimiento",
                    mensaje=(
                        f"Posible duplicado detectado al registrar persona #{id_persona}: "
                        f"similitud {sim:.4f} con persona #{p_existente.id_persona}"
                    ),
                    commit=True,
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensaje": "Posible rostro duplicado detectado.",
                        "similitud": round(sim, 4),
                        "persona_similar": {
                            "id_persona": p_existente.id_persona,
                            "nombre": p_existente.nombre,
                            "apellidos": p_existente.apellidos,
                            "rol": p_existente.rol,
                        },
                        "sugerencia": (
                            "Si deseas continuar de todas formas, "
                            "envía la petición con el parámetro ?forzar=true"
                        ),
                    },
                )
 
    # Guardar imagen en disco
    os.makedirs(directorio_fotos, exist_ok=True)
    nombre_archivo = f"{id_persona}_{imagen.filename}"
    ruta = os.path.join(directorio_fotos, nombre_archivo)
    with open(ruta, "wb") as f:
        f.write(contenido)
 
    # Persistir embedding y ruta
    rostro = RostroAutorizado(
        id_persona=id_persona,
        embedding=embedding.tolist(),
        descripcion="Registro automático",
        ruta_imagen=ruta,
    )
    db.add(rostro)

    persona.ruta_rostro = ruta
    registrar_log(
        db,
        nivel="INFO",
        origen="Motor_IA",
        tipo="Reconocimiento",
        mensaje=f"Embedding registrado para persona autorizada #{id_persona}",
    )
    db.commit()
    db.refresh(persona)
    return _a_schema(persona, db)


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
        registrar_log(
            db,
            nivel="WARNING",
            origen="Motor_IA",
            tipo="Reconocimiento",
            mensaje=f"Error al extraer embedding en identificacion: {e}",
            commit=True,
        )
        raise HTTPException(status_code=422, detail=str(e))

    # Buscar la mejor coincidencia entre personas registradas usando pgvector
    distancia = RostroAutorizado.embedding.cosine_distance(embedding_nuevo.tolist())
    coincidencia = (
        db.query(RostroAutorizado, PersonaAutorizada, distancia.label("distancia"))
        .join(
            PersonaAutorizada,
            PersonaAutorizada.id_persona == RostroAutorizado.id_persona,
        )
        .filter(RostroAutorizado.embedding.isnot(None))
        .order_by(distancia)
        .first()
    )

    mejor_similitud = -1.0
    mejor_persona: Optional[PersonaAutorizada] = None

    if coincidencia:
        _, mejor_persona, mejor_distancia = coincidencia
        mejor_similitud = 1.0 - float(mejor_distancia)

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

    if tipo_acceso == "No Autorizado":
        embedding_detectado = embedding_nuevo.tolist()
        ruta_captura = None
        try:
            directorio_intrusos = os.getenv("DIRECTORIO_INTRUSOS", "capturas_intrusos")
            os.makedirs(directorio_intrusos, exist_ok=True)
 
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            nombre_archivo = f"intruso_ev{evento.id_evento}_{timestamp}.jpg"
            ruta_captura = os.path.join(directorio_intrusos, nombre_archivo)
 
            with open(ruta_captura, "wb") as f:
                f.write(contenido)
 
            registrar_log(
                db,
                nivel="INFO",
                origen="Motor_IA",
                tipo="Reconocimiento",
                mensaje=f"Imagen de intruso guardada en: {ruta_captura}",
            )
        except Exception as e_img:
            registrar_log(
                db,
                nivel="WARNING",
                origen="Motor_IA",
                tipo="Reconocimiento",
                mensaje=f"No se pudo guardar la imagen del intruso: {e_img}",
            )
            ruta_captura = None

        pna = PersonaNoAutorizada(
            embedding_detectado=embedding_detectado,
            ruta_imagen_captura=ruta_captura,   # ← campo ahora poblado
        )
        db.add(pna)

    registrar_log(
        db,
        nivel="INFO",
        origen="Motor_IA",
        tipo="Reconocimiento",
        mensaje=(
            f"Evento de acceso generado. tipo={tipo_acceso}, "
            f"id_persona={id_persona}, camara={id_camara}, similitud={round(mejor_similitud, 4)}"
        ),
    )

    db.commit()
    db.refresh(evento)

    if tipo_acceso == "No Autorizado":
        try:
            alerta_ws = notificacion_service.notificar_intrusion(db, evento)
            await alertas_ws_manager.broadcast_json({
                "type": "alerta_nueva",
                "data": alerta_ws,
            })
            registrar_log(
                db,
                nivel="INFO",
                origen="Motor_IA",
                tipo="Notificacion",
                id_evento=evento.id_evento,
                mensaje="Notificacion de intrusion disparada correctamente",
                commit=True,
            )
        except Exception as e:
            import traceback
            db.rollback()
            log_msg = f"Fallo notificacion: {e}\n{traceback.format_exc()}"
            print(log_msg)
            registrar_log(
                db,
                nivel="ERROR",
                origen="Motor_IA",
                tipo="Notificacion",
                id_evento=evento.id_evento,
                mensaje=log_msg,
                commit=True,
            )

    return ResultadoReconocimiento(
        tipo_acceso=tipo_acceso,
        similitud=round(mejor_similitud, 4),
        id_persona=mejor_persona.id_persona if mejor_persona and tipo_acceso == "Autorizado" else None,
        nombre=mejor_persona.nombre if mejor_persona and tipo_acceso == "Autorizado" else None,
        apellidos=mejor_persona.apellidos if mejor_persona and tipo_acceso == "Autorizado" else None,
        id_evento=evento.id_evento,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _a_schema(persona: PersonaAutorizada, db: Optional[Session] = None) -> DatosPersonaAutorizada:
    tiene_embedding = False
    if db is not None:
        tiene_embedding = (
            db.query(RostroAutorizado)
            .filter(RostroAutorizado.id_persona == persona.id_persona)
            .first()
            is not None
        )
    elif persona.ruta_rostro is not None:
        # Fallback para llamadas sin sesión (retrocompatibilidad)
        tiene_embedding = True

    return DatosPersonaAutorizada(
        id_persona=persona.id_persona,
        nombre=persona.nombre,
        apellidos=persona.apellidos,
        email=persona.email,
        telefono=persona.telefono,
        id_cubiculo=persona.id_cubiculo,
        rol=persona.rol,
        ruta_rostro=persona.ruta_rostro,
        tiene_embedding=tiene_embedding,
        fecha_registro=persona.fecha_registro,
    )