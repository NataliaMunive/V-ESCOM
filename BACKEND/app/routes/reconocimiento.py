"""
Router del módulo de reconocimiento facial.
Todas las rutas requieren autenticación JWT (admin).
"""
from typing import List, Optional, Union, Dict
import threading
import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from app.bd import get_db, SessionLocal
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.evento import EventoAcceso
from app.schemas.reconocimiento_schema import (
    CrearPersonaAutorizada,
    DatosEvento,
    DatosPersonaAutorizada,
    ResultadoEntrenamiento,
    ResultadoReconocimiento,
    ResultadoReconocimientoMultiples,
    ResultadoSubidaMultiple,
    ResumenEventos,
    UpdPersonaAutorizada,
)
from app.services import entrenamiento_service, reconocimiento_service
from app.services.websocket_manager import alertas_ws_manager
import traceback
import time

router = APIRouter(prefix="/reconocimiento", tags=["Reconocimiento Facial"])


# ─── CRUD Personas Autorizadas ────────────────────────────────────────────────

@router.post(
    "/personas",
    response_model=DatosPersonaAutorizada,
    status_code=201,
    summary="Registrar persona autorizada",
)
def crear_persona(
    datos: CrearPersonaAutorizada,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    return reconocimiento_service.crear_persona(db, datos)


@router.get(
    "/personas",
    response_model=List[DatosPersonaAutorizada],
    summary="Listar personas autorizadas",
)
def listar_personas(
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    personas = reconocimiento_service.obtener_personas(db)
    return [reconocimiento_service._a_schema(p, db) for p in personas]


@router.get(
    "/personas/{id_persona}",
    response_model=DatosPersonaAutorizada,
    summary="Obtener persona por ID",
)
def obtener_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    p = reconocimiento_service.obtener_persona(db, id_persona)
    return reconocimiento_service._a_schema(p, db)


@router.put(
    "/personas/{id_persona}",
    response_model=DatosPersonaAutorizada,
    summary="Actualizar persona autorizada",
)
def actualizar_persona(
    id_persona: int,
    datos: UpdPersonaAutorizada,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    p = reconocimiento_service.actualizar_persona(db, id_persona, datos)
    return reconocimiento_service._a_schema(p, db)


@router.delete(
    "/personas/{id_persona}",
    summary="Eliminar persona autorizada",
)
def eliminar_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    reconocimiento_service.eliminar_persona(db, id_persona)
    return {"message": "Persona eliminada correctamente"}


# ─── Gestión de rostros ───────────────────────────────────────────────────────

@router.post(
    "/personas/{id_persona}/rostro",
    response_model=DatosPersonaAutorizada,
    summary="Subir foto y generar embedding",
)
async def registrar_rostro(
    id_persona: int,
    imagen: UploadFile = File(..., description="Foto del rostro (JPEG/PNG, 1 sola cara)"),
    forzar: bool = Query(
        False,
        description=(
            "Si es true, omite la verificación de duplicados y guarda el embedding "
            "aunque exista una persona similar registrada."
        ),
    ),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    """
    Sube la imagen de referencia de una persona autorizada,
    extrae el embedding ArcFace y lo almacena en la BD.
 
    Antes de guardar, verifica que no exista un rostro similar en la base de datos
    (detección de duplicados - CU05 flujo alterno 2a).
    Si se detecta un posible duplicado, retorna HTTP 409 con los datos de la persona similar.
    Para continuar de todas formas, envía ?forzar=true.
    """
    return await reconocimiento_service.registrar_rostro(
        db, id_persona, imagen, forzar=forzar
    )


@router.post(
    "/personas/{id_persona}/rostros",
    response_model=ResultadoSubidaMultiple,
    summary="Subir múltiples fotos y generar embeddings",
)
async def registrar_rostros_multiples(
    id_persona: int,
    imagenes: List[UploadFile] = File(
        ...,
        description="Lista de fotos del rostro (JPEG/PNG, idealmente distintos ángulos)",
    ),
    forzar: bool = Query(
        False,
        description=(
            "Si es true, omite verificación de duplicados por cada imagen y guarda "
            "los embeddings aunque exista una persona similar."
        ),
    ),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    if not imagenes:
        raise HTTPException(status_code=422, detail="Debes enviar al menos una imagen.")

    resultado = await reconocimiento_service.registrar_multiples_rostros(
        db=db,
        id_persona=id_persona,
        imagenes=imagenes,
        forzar=forzar,
    )
    if resultado.exitosas == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": "No se pudo registrar ninguna imagen del lote.",
                "resultado": resultado.model_dump(),
            },
        )
    return resultado
 


# ─── Modelo SVM ───────────────────────────────────────────────────────────────

@router.post(
    "/modelo/recargar",
    summary="Recargar modelo SVM tras reentrenamiento",
)
def recargar_modelo(
    _: Administrador = Depends(get_current_admin),
):
    """
    Fuerza la recarga del modelo SVM desde disco sin reiniciar el servidor.

    Llama a este endpoint **después** de ejecutar `entrenar_clasificador.py`
    para que el servicio use el modelo actualizado de inmediato.

    - Si el modelo existe y se cargó bien → `{"modelo": "svm", "estado": "cargado"}`
    - Si el archivo no existe aún       → `{"modelo": "coseno", "estado": "sin_modelo"}`
    """
    cargado = reconocimiento_service.recargar_modelo_svm()
    if cargado:
        return {"modelo": "svm", "estado": "cargado", "ruta": str(reconocimiento_service._RUTA_MODELO_SVM)}
    return {"modelo": "coseno", "estado": "sin_modelo", "mensaje": "No se encontró el archivo .joblib. Usa el método coseno."}


@router.post(
    "/entrenar",
    response_model=ResultadoEntrenamiento,
    summary="Entrenar clasificador SVM con embeddings de la BD",
)
@router.post(
    "/entrenar",
    summary="Entrenar clasificador SVM con embeddings de la BD (asíncrono, notifica por WebSocket)",
)
def entrenar_modelo(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    """
    Lanza el entrenamiento en background y responde inmediatamente.

    El worker en background ejecuta `ejecutar_entrenamiento`, fuerza la recarga
    del modelo SVM y envía via WebSocket el evento
    `{type: 'entrenamiento_completado', data: resultado}` cuando termina.
    """

    def _worker():
        db_bg = SessionLocal()
        start = time.time()
        try:
            try:
                resultado = entrenamiento_service.ejecutar_entrenamiento(db_bg)
                # Forzar recarga del modelo en este proceso
                reconocimiento_service.recargar_modelo_svm()
                resultado_ok = True
            except Exception as ex:
                resultado_ok = False
                tb = traceback.format_exc()
                resultado = {"error": str(ex), "mensaje": "Fallo durante el entrenamiento", "traceback": tb[:4000]}

            # Añadir metadatos temporales
            resultado["timestamp"] = int(time.time())
            resultado["duration_seconds"] = round(time.time() - start, 2)

            payload = {"type": "entrenamiento_completado", "data": resultado}
            try:
                # Ejecutar broadcast en un loop nuevo (estamos en hilo separado)
                asyncio.run(alertas_ws_manager.broadcast_json(payload))
            except Exception:
                # Si falla el broadcast no interrumpimos el worker
                pass
        finally:
            db_bg.close()

    # Encolar el inicio del hilo para que se dispare una vez que la respuesta haya sido enviada
    background_tasks.add_task(threading.Thread(target=_worker, daemon=True).start)
    return {"mensaje": "Entrenamiento iniciado"}


@router.get(
    "/modelo/estado",
    summary="Consultar qué método de identificación está activo",
)
def estado_modelo(
    _: Administrador = Depends(get_current_admin),
):
    """
    Informa si el sistema usará el modelo SVM entrenado o la búsqueda coseno.
    """
    artefacto = reconocimiento_service._cargar_modelo_svm()
    if artefacto is not None:
        num_personas = artefacto.get("num_personas", "?")
        kernel = artefacto.get("kernel", "?")
        return {
            "metodo_activo": "svm",
            "num_personas": num_personas,
            "kernel": kernel,
            "ruta_modelo": str(reconocimiento_service._RUTA_MODELO_SVM),
        }
    return {
        "metodo_activo": "coseno",
        "mensaje": "No hay modelo SVM cargado. Entrena con entrenar_clasificador.py y llama a /modelo/recargar.",
    }


# ─── Identificación ───────────────────────────────────────────────────────────

@router.post(
    "/identificar",
    response_model=ResultadoReconocimiento,
    summary="Identificar rostro (autorizado / no autorizado)",
)
async def identificar(
    imagen: UploadFile = File(..., description="Frame capturado por la cámara"),
    id_camara: Optional[int] = Form(None, description="ID de la cámara que capturó el frame"),
    modo: str = Query(
        "auto",
        description="Modo de identificación: auto, svm o coseno (prueba rápida)",
    ),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    """
    Recibe un frame de cámara, extrae el embedding y lo compara usando:
    - **Modelo SVM** (si existe `modelos/clasificador_svm.joblib`) → más preciso con múltiples ángulos.
    - **Distancia coseno** (fallback automático) → modo prueba rápida sin reentrenamiento.

    El parámetro `modo` permite forzar:
    - `auto`: usa SVM si existe; si no, usa coseno.
    - `svm`: fuerza el modelo entrenado.
    - `coseno`: fuerza la prueba rápida por distancia coseno.
    """
    return await reconocimiento_service.identificar_rostro(db, imagen, id_camara, modo=modo)


@router.post(
    "/identificar/multiples",
    response_model=ResultadoReconocimientoMultiples,
    summary="Identificar múltiples rostros en una sola imagen",
)
async def identificar_multiples(
    imagen: UploadFile = File(..., description="Imagen con uno o varios rostros"),
    id_camara: Optional[int] = Form(None, description="ID de la cámara que capturó el frame"),
    modo: str = Query(
        "auto",
        description="Modo de identificación: auto, svm o coseno",
    ),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    return await reconocimiento_service.identificar_rostros_multiples(db, imagen, id_camara, modo=modo)


# ─── Historial de eventos ─────────────────────────────────────────────────────

@router.get(
    "/eventos",
    response_model=Union[List[DatosEvento], Dict[str, str]],
    summary="Historial de eventos de acceso",
)
def listar_eventos(
    tipo: Optional[str] = Query(None, description="Filtrar: 'Autorizado' o 'No Autorizado'"),
    id_camara: Optional[int] = Query(None),
    id_persona: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    query = db.query(EventoAcceso)
    if tipo:
        query = query.filter(EventoAcceso.tipo_acceso == tipo)
    if id_camara:
        query = query.filter(EventoAcceso.id_camara == id_camara)
    if id_persona:
        query = query.filter(EventoAcceso.id_persona == id_persona)
    eventos = query.order_by(EventoAcceso.id_evento.desc()).limit(limit).all()
    if not eventos:
        return {"message": "No hay eventos"}
    return eventos


@router.get(
    "/eventos/resumen",
    response_model=ResumenEventos,
    summary="Resumen agregado de eventos",
)
def resumen_eventos(
    tipo: Optional[str] = Query(None, description="Filtrar: 'Autorizado' o 'No Autorizado'"),
    id_camara: Optional[int] = Query(None),
    id_persona: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Administrador = Depends(get_current_admin),
):
    query = db.query(EventoAcceso)
    if tipo:
        query = query.filter(EventoAcceso.tipo_acceso == tipo)
    if id_camara:
        query = query.filter(EventoAcceso.id_camara == id_camara)
    if id_persona:
        query = query.filter(EventoAcceso.id_persona == id_persona)

    total = query.count()
    autorizados = query.filter(EventoAcceso.tipo_acceso == "Autorizado").count()
    no_autorizados = query.filter(EventoAcceso.tipo_acceso == "No Autorizado").count()
    tasa_acceso = round((autorizados / total) * 100, 1) if total else 0.0

    return {
        "total": total,
        "autorizados": autorizados,
        "no_autorizados": no_autorizados,
        "tasa_acceso": tasa_acceso,
    }