from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.models.evento import EventoAcceso, PersonaNoAutorizada
from app.models.persona_autorizada import PersonaAutorizada
from app.models.profesor import Profesor
from app.models.rostro_autorizado import RostroAutorizado
from app.models.administrador import Administrador  # Importación clave
from app.schemas.reconocimiento_schema import (
    CrearPersonaAutorizada,
    DatosPersonaAutorizada,
    ResultadoImagen,
    ResultadoReconocimiento,
    ResultadoReconocimientoMultiples,
    ResultadoReconocimientoRostro,
    ResultadoSubidaMultiple,
    UpdPersonaAutorizada,
)
from app.services import notificacion_service
from app.services.log_sistema_service import registrar_log
from app.services.websocket_manager import alertas_ws_manager
from app.utils.face_utils import bytes_a_bgr, detectar_rostros, extraer_embedding
from app.utils.phone_utils import normalizar_telefono_mx

# ─── Control de Notificaciones (Throttling) ──────────────────────────────────
_contador_intrusos_por_camara: dict[int, int] = {}
LIMITE_DETECCIONES_NOTIFICACION = int(os.getenv("LIMITE_DETECCIONES_NOTIFICACION", "10"))
# ─────────────────────────────────────────────────────────────────────────────

# Umbrales por método:
# - SVM: probabilidad del clasificador (recomendado >= 0.60)
# - Coseno: similitud ArcFace (recomendado >= 0.45)
SIMILITUD_UMBRAL = float(os.getenv("SIMILITUD_UMBRAL", "0.40"))
SIMILITUD_UMBRAL_COSENO = float(
    os.getenv("SIMILITUD_UMBRAL_COSENO", str(max(SIMILITUD_UMBRAL, 0.45)))
)
PROBABILIDAD_UMBRAL_SVM = float(
    os.getenv("PROBABILIDAD_UMBRAL_SVM", str(max(SIMILITUD_UMBRAL, 0.60)))
)
MODOS_IDENTIFICACION = {"auto", "svm", "coseno"}

# Ruta del modelo SVM entrenado (configurable desde .env)
_RUTA_MODELO_SVM = Path(
    os.getenv("RUTA_MODELO_SVM", "modelos/clasificador_svm.joblib")
)

# ─── Gestión del modelo SVM (singleton con recarga) ───────────────────────────

_modelo_svm_cache: dict[str, Any] = {}   # claves: "pipeline", "codificador_etiquetas"
_modelo_svm_cargado: bool = False
_modelo_svm_mtime: float | None = None


def _cargar_modelo_svm(forzar_recarga: bool = False) -> dict[str, Any] | None:
    global _modelo_svm_cache, _modelo_svm_cargado, _modelo_svm_mtime

    if forzar_recarga:
        _modelo_svm_cache = {}
        _modelo_svm_cargado = False
        _modelo_svm_mtime = None

    if _modelo_svm_cargado and not forzar_recarga:
        if _RUTA_MODELO_SVM.exists():
            try:
                mtime_actual = _RUTA_MODELO_SVM.stat().st_mtime
                if _modelo_svm_mtime is not None and mtime_actual <= _modelo_svm_mtime:
                    return _modelo_svm_cache if _modelo_svm_cache else None
                _modelo_svm_cache = {}
                _modelo_svm_cargado = False
                _modelo_svm_mtime = None
            except Exception:
                return _modelo_svm_cache if _modelo_svm_cache else None
        else:
            return _modelo_svm_cache if _modelo_svm_cache else None

    _modelo_svm_cargado = True  

    if not _RUTA_MODELO_SVM.exists():
        _modelo_svm_mtime = None
        return None

    try:
        import joblib
        artefacto = joblib.load(_RUTA_MODELO_SVM)
        _modelo_svm_mtime = _RUTA_MODELO_SVM.stat().st_mtime
        if "pipeline" in artefacto and "codificador_etiquetas" in artefacto:
            _modelo_svm_cache = artefacto
            return _modelo_svm_cache
        if "modelo" in artefacto and "codificador" in artefacto:
            _modelo_svm_cache = {
                "pipeline": artefacto["modelo"],
                "codificador_etiquetas": artefacto["codificador"],
            }
            return _modelo_svm_cache
        return None
    except Exception as e:
        print(f"[WARN] No se pudo cargar el modelo SVM: {e}")
        return None


def recargar_modelo_svm() -> bool:
    """Fuerza la recarga del modelo SVM desde disco."""
    artefacto = _cargar_modelo_svm(forzar_recarga=True)
    return artefacto is not None


def _identificar_con_svm(
    embedding: np.ndarray,
    artefacto: dict[str, Any],
) -> tuple[int | None, float]:
    pipeline = artefacto["pipeline"]
    codificador = artefacto["codificador_etiquetas"]
    vector = embedding.reshape(1, -1)
    probabilidades = pipeline.predict_proba(vector)[0]
    indice_mejor = int(np.argmax(probabilidades))
    probabilidad_mejor = float(probabilidades[indice_mejor])
    id_persona = int(codificador.inverse_transform([indice_mejor])[0])
    return id_persona, probabilidad_mejor


def _identificar_por_coseno(
    db: Session,
    embedding_nuevo: np.ndarray,
) -> tuple[Optional[PersonaAutorizada], float]:
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
    return mejor_persona, mejor_similitud


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


def _recortar_imagen_por_bbox(imagen_bytes: bytes, bbox: tuple[int, int, int, int]) -> bytes:
    img_bgr = bytes_a_bgr(imagen_bytes)
    alto, ancho = img_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    margen_x = int((x2 - x1) * 0.2)
    margen_y = int((y2 - y1) * 0.2)
    x1 = max(0, x1 - margen_x)
    y1 = max(0, y1 - margen_y)
    x2 = min(ancho, x2 + margen_x)
    y2 = min(alto, y2 + margen_y)
    if x2 <= x1 or y2 <= y1:
        return imagen_bytes

    recorte = img_bgr[y1:y2, x1:x2]
    exito, buffer = cv2.imencode(".jpg", recorte, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not exito:
        return imagen_bytes
    return buffer.tobytes()


def _a_schema(persona: PersonaAutorizada, db: Session) -> DatosPersonaAutorizada:
    """Convierte una `PersonaAutorizada` de SQLAlchemy al esquema `DatosPersonaAutorizada`.

    Añade el campo `tiene_embedding` consultando la tabla `rostros_autorizados`.
    """
    tiene = (
        db.query(RostroAutorizado)
        .filter(RostroAutorizado.id_persona == persona.id_persona)
        .filter(RostroAutorizado.embedding.isnot(None))
        .first()
        is not None
    )

    datos = {
        "id_persona": persona.id_persona,
        "nombre": persona.nombre,
        "apellidos": persona.apellidos,
        "email": persona.email,
        "telefono": persona.telefono,
        "id_cubiculo": persona.id_cubiculo,
        "rol": persona.rol,
        "ruta_rostro": persona.ruta_rostro,
        "tiene_embedding": bool(tiene),
        "fecha_registro": getattr(persona, "fecha_registro", None),
    }
    return DatosPersonaAutorizada(**datos)


class _BytesUpload:
    def __init__(self, contenido: bytes):
        self.filename = "rostro.jpg"
        self._contenido = contenido
    async def read(self) -> bytes:
        return self._contenido

# ─── CRUD Personas Autorizadas ────────────────────────────────────────────────

def crear_persona(db: Session, datos: CrearPersonaAutorizada) -> PersonaAutorizada:
    datos_dict = datos.model_dump()
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
    persona = obtener_persona(db, id_persona)
    contenido = await imagen.read()
 
    try:
        embedding = await run_in_threadpool(extraer_embedding, contenido)
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
        UMBRAL_DUPLICADO = float(
            os.getenv("SIMILITUD_UMBRAL_COSENO", str(SIMILITUD_UMBRAL_COSENO))
        )
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
 
    os.makedirs(directorio_fotos, exist_ok=True)
    nombre_archivo = f"{id_persona}_{imagen.filename}"
    ruta = os.path.join(directorio_fotos, nombre_archivo)
    with open(ruta, "wb") as f:
        f.write(contenido)
 
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


async def registrar_multiples_rostros(
    db: Session,
    id_persona: int,
    imagenes: list[UploadFile],
    directorio_fotos: str = "fotos_rostros",
    forzar: bool = False,
) -> ResultadoSubidaMultiple:
    obtener_persona(db, id_persona)
    resultados: list[ResultadoImagen] = []
    exitosas = 0

    for imagen in imagenes:
        nombre_archivo = imagen.filename or "archivo_sin_nombre"
        try:
            await registrar_rostro(
                db=db,
                id_persona=id_persona,
                imagen=imagen,
                directorio_fotos=directorio_fotos,
                forzar=forzar,
            )
            resultados.append(
                ResultadoImagen(
                    nombre_archivo=nombre_archivo,
                    estado="ok",
                    detalle="Embedding registrado correctamente.",
                )
            )
            exitosas += 1
        except HTTPException as exc:
            estado = "error"
            similitud = None
            detalle = "No se pudo procesar la imagen."
            if isinstance(exc.detail, dict):
                detalle = str(exc.detail.get("mensaje", detalle))
                if exc.status_code == 409:
                    estado = "duplicado"
                    similitud_val = exc.detail.get("similitud")
                    if similitud_val is not None:
                        similitud = float(similitud_val)
            elif isinstance(exc.detail, str):
                detalle = exc.detail
            resultados.append(
                ResultadoImagen(
                    nombre_archivo=nombre_archivo,
                    estado=estado,
                    detalle=detalle,
                    similitud=similitud,
                )
            )
        except Exception as exc:
            resultados.append(
                ResultadoImagen(
                    nombre_archivo=nombre_archivo,
                    estado="error",
                    detalle=f"Error inesperado: {exc}",
                )
            )

    total = len(imagenes)
    fallidas = total - exitosas
    return ResultadoSubidaMultiple(
        id_persona=id_persona,
        total_recibidas=total,
        exitosas=exitosas,
        fallidas=fallidas,
        resultados=resultados,
    )


async def _procesar_embedding_reconocimiento(
    db: Session,
    embedding_nuevo: np.ndarray,
    contenido: bytes,
    id_camara: Optional[int] = None,
    modo: str = "auto",
) -> ResultadoReconocimiento:
    modo_normalizado = (modo or "auto").strip().lower()
    if modo_normalizado not in MODOS_IDENTIFICACION:
        raise HTTPException(
            status_code=400,
            detail=(
                "Modo de identificación inválido. Usa 'auto', 'svm' o 'coseno'."
            ),
        )

    mejor_similitud = -1.0
    mejor_persona: Optional[PersonaAutorizada] = None
    metodo_usado = "coseno"
    umbral_usado = SIMILITUD_UMBRAL_COSENO
    svm_fallo = False
    persona_svm: Optional[PersonaAutorizada] = None
    similitud_svm = -1.0
    persona_coseno: Optional[PersonaAutorizada] = None
    similitud_coseno = -1.0

    artefacto_svm = _cargar_modelo_svm() if modo_normalizado != "coseno" else None
    if modo_normalizado == "svm" and artefacto_svm is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No hay modelo SVM disponible. Ejecuta el entrenamiento "
                "o usa modo='coseno' para la prueba rápida."
            ),
        )

    if artefacto_svm is not None and modo_normalizado in {"auto", "svm"}:
        try:
            id_persona_svm, probabilidad = await run_in_threadpool(
                _identificar_con_svm,
                embedding_nuevo,
                artefacto_svm,
            )
            if probabilidad >= PROBABILIDAD_UMBRAL_SVM:
                persona_svm = (
                    db.query(PersonaAutorizada)
                    .filter(PersonaAutorizada.id_persona == id_persona_svm)
                    .first()
                )
                if persona_svm is not None:
                    similitud_svm = probabilidad
        except Exception as e_svm:
            svm_fallo = True
            registrar_log(
                db,
                nivel="WARNING",
                origen="Motor_IA",
                tipo="Reconocimiento",
                mensaje=f"Fallo SVM, usando coseno como fallback: {e_svm}",
                commit=False,
            )

    usar_coseno = (
        modo_normalizado == "coseno"
        or artefacto_svm is None
        or modo_normalizado == "auto"
        or (modo_normalizado == "svm" and persona_svm is None)
    )
    if usar_coseno:
        persona_coseno, similitud_coseno = _identificar_por_coseno(db, embedding_nuevo)

    if modo_normalizado == "svm":
        if persona_svm is not None:
            mejor_persona = persona_svm
            mejor_similitud = similitud_svm
            metodo_usado = "svm"
            umbral_usado = PROBABILIDAD_UMBRAL_SVM
    elif modo_normalizado == "coseno":
        if persona_coseno is not None:
            mejor_persona = persona_coseno
            mejor_similitud = similitud_coseno
            metodo_usado = "coseno"
            umbral_usado = SIMILITUD_UMBRAL_COSENO
    elif modo_normalizado == "svm":
        if persona_svm is not None:
            mejor_persona = persona_svm
            mejor_similitud = similitud_svm
            metodo_usado = "svm"
            umbral_usado = PROBABILIDAD_UMBRAL_SVM
    else:
        candidatos: list[tuple[str, float, PersonaAutorizada, float]] = []
        if persona_svm is not None:
            candidatos.append(("svm", similitud_svm, persona_svm, PROBABILIDAD_UMBRAL_SVM))
        if persona_coseno is not None:
            candidatos.append(("coseno", similitud_coseno, persona_coseno, SIMILITUD_UMBRAL_COSENO))

        if candidatos:
            metodo_usado, mejor_similitud, mejor_persona, umbral_usado = max(
                candidatos,
                key=lambda item: item[1],
            )

    if mejor_persona and mejor_similitud >= umbral_usado:
        tipo_acceso = "Autorizado"
        id_persona = mejor_persona.id_persona
    else:
        tipo_acceso = "No Autorizado"
        id_persona = None

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

            # --- INTEGRACIÓN TELEGRAM ---
            try:
                admins = db.query(Administrador).filter(Administrador.telegram_chat_id.isnot(None)).all()
                for admin in admins:
                    notificacion_service.enviar_alerta_telegram(
                        mensaje=f"🚨 Intruso detectado en cámara #{id_camara or 'Desconocida'}",
                        ruta_imagen=ruta_captura,
                        chat_id=admin.telegram_chat_id
                    )
            except Exception as e_tg:
                print(f"Error al enviar notificación de Telegram: {e_tg}")

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
            ruta_imagen_captura=ruta_captura,
        )
        db.add(pna)

    registrar_log(
        db,
        nivel="INFO",
        origen="Motor_IA",
        tipo="Reconocimiento",
        mensaje=(
            f"Evento de acceso generado. tipo={tipo_acceso}, "
            f"id_persona={id_persona}, camara={id_camara}, "
            f"similitud={round(mejor_similitud, 4)}, "
            f"metodo={metodo_usado}, modo={modo_normalizado}, umbral={round(umbral_usado, 4)}"
        ),
    )

    db.commit()
    db.refresh(evento)

    if tipo_acceso == "No Autorizado":
        camara_key = id_camara if id_camara is not None else -1
        _contador_intrusos_por_camara[camara_key] = _contador_intrusos_por_camara.get(camara_key, 0) + 1
        contador_actual = _contador_intrusos_por_camara[camara_key]
        
        toca_enviar_sms = (contador_actual >= LIMITE_DETECCIONES_NOTIFICACION)

        if toca_enviar_sms:
            _contador_intrusos_por_camara[camara_key] = 0
            mensaje_log = f"Notificación SMS disparada tras {LIMITE_DETECCIONES_NOTIFICACION} detecciones"
        else:
            mensaje_log = f"Detección {contador_actual}/{LIMITE_DETECCIONES_NOTIFICACION} guardada. SMS omitido."

        try:
            alerta_ws = notificacion_service.notificar_intrusion(db, evento, enviar_sms=toca_enviar_sms)
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
                mensaje=mensaje_log,
                commit=True,
            )

        except Exception as e:
            import traceback
            db.rollback()
            log_msg = f"Fallo notificacion WS/SMS: {e}\n{traceback.format_exc()}"
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


async def identificar_rostro(
    db: Session,
    imagen: UploadFile,
    id_camara: Optional[int] = None,
    modo: str = "auto",
) -> ResultadoReconocimiento:
    contenido = await imagen.read()

    try:
        embedding_nuevo = await run_in_threadpool(extraer_embedding, contenido)
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

    return await _procesar_embedding_reconocimiento(db, embedding_nuevo, contenido, id_camara=id_camara, modo=modo)


async def identificar_rostros_multiples(
    db: Session,
    imagen: UploadFile,
    id_camara: Optional[int] = None,
    modo: str = "auto",
) -> ResultadoReconocimientoMultiples:
    contenido = await imagen.read()

    try:
        rostros = await run_in_threadpool(detectar_rostros, contenido)
    except ValueError as e:
        registrar_log(
            db,
            nivel="WARNING",
            origen="Motor_IA",
            tipo="Reconocimiento",
            mensaje=f"Error al detectar rostros múltiples: {e}",
            commit=True,
        )
        raise HTTPException(status_code=422, detail=str(e))

    resultados: list[ResultadoReconocimientoRostro] = []
    for indice, rostro in enumerate(rostros, start=1):
        try:
            resultado = await _procesar_embedding_reconocimiento(
                db,
                rostro.embedding,
                contenido,
                id_camara=id_camara,
                modo=modo,
            )
            resultados.append(
                ResultadoReconocimientoRostro(
                    indice_rostro=indice,
                    bbox=list(rostro.bbox),
                    estado="ok",
                    tipo_acceso=resultado.tipo_acceso,
                    similitud=resultado.similitud,
                    id_persona=resultado.id_persona,
                    nombre=resultado.nombre,
                    apellidos=resultado.apellidos,
                    id_evento=resultado.id_evento,
                )
            )
        except HTTPException as exc:
            detalle = exc.detail
            if isinstance(detalle, dict):
                detalle = detalle.get("mensaje", str(detalle))
            resultados.append(
                ResultadoReconocimientoRostro(
                    indice_rostro=indice,
                    bbox=list(rostro.bbox),
                    estado="error",
                    detalle=str(detalle),
                )
            )

    return ResultadoReconocimientoMultiples(
        total_detectados=len(rostros),
        resultados=resultados,
    )