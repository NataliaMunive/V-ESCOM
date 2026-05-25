"""Servicio de entrenamiento SVM para reconocimiento facial.

Este módulo encapsula el flujo de entrenamiento para ejecutarlo desde FastAPI,
reutilizando la sesión de BD de la petición y devolviendo resultados en JSON.
"""

from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from fastapi import HTTPException
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, Normalizer
from sklearn.svm import SVC
from sqlalchemy.orm import Session

from app.models.persona_autorizada import PersonaAutorizada
from app.models.rostro_autorizado import RostroAutorizado

_RUTA_MODELO_SVM = Path(
    os.getenv("RUTA_MODELO_SVM", "modelos/clasificador_svm.joblib")
)
_SVM_PARAM_C = float(os.getenv("SVM_PARAM_C", "5.0"))
_SVM_KERNEL = os.getenv("SVM_KERNEL", "rbf")
_SVM_SEMILLA = int(os.getenv("SVM_SEMILLA", "42"))
_SVM_PLIEGUES = int(os.getenv("SVM_PLIEGUES", "5"))
_SVM_PLIEGUES_MAX = int(os.getenv("SVM_PLIEGUES_MAX", "5"))
_SVM_MAX_EMBEDDINGS = int(os.getenv("SVM_MAX_EMBEDDINGS", "5000"))


def _cargar_embeddings(db: Session) -> tuple[np.ndarray, np.ndarray]:
    consulta = (
        db.query(RostroAutorizado.id_persona, RostroAutorizado.embedding)
        .filter(RostroAutorizado.embedding.isnot(None))
        .order_by(RostroAutorizado.id_rostro.desc())
    )
    if _SVM_MAX_EMBEDDINGS > 0:
        consulta = consulta.limit(_SVM_MAX_EMBEDDINGS)
    filas = consulta.all()
    if not filas:
        raise HTTPException(
            status_code=422,
            detail="No hay embeddings registrados en la base de datos.",
        )

    matriz_x = np.array(
        [np.array(fila.embedding, dtype=np.float32) for fila in filas],
        dtype=np.float32,
    )
    vector_y = np.array([int(fila.id_persona) for fila in filas], dtype=np.int32)
    return matriz_x, vector_y


def _crear_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("normalizador", Normalizer(norm="l2")),
            (
                "clasificador",
                SVC(
                    C=_SVM_PARAM_C,
                    kernel=_SVM_KERNEL,
                    probability=True,
                    random_state=_SVM_SEMILLA,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def _validar_y_filtrar_personas(
    db: Session,
    matriz_x: np.ndarray,
    vector_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    clases, conteos = np.unique(vector_y, return_counts=True)
    ids_validos = clases[conteos >= 2]
    ids_filtrados = clases[conteos < 2]

    if len(ids_validos) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                "Entrenamiento no disponible: se requieren al menos 2 personas "
                "con 2 o más embeddings cada una."
            ),
        )

    mascara = np.isin(vector_y, ids_validos)
    x_filtrado = matriz_x[mascara]
    y_filtrado = vector_y[mascara]

    if len(ids_filtrados) == 0:
        return x_filtrado, y_filtrado, []

    nombres = (
        db.query(PersonaAutorizada.id_persona, PersonaAutorizada.nombre, PersonaAutorizada.apellidos)
        .filter(PersonaAutorizada.id_persona.in_([int(v) for v in ids_filtrados.tolist()]))
        .all()
    )
    omitidos = [
        f"{fila.id_persona}:{fila.nombre} {fila.apellidos or ''}".strip()
        for fila in nombres
    ]
    return x_filtrado, y_filtrado, omitidos


def ejecutar_entrenamiento(db: Session) -> dict[str, object]:
    matriz_x, vector_y = _cargar_embeddings(db)
    matriz_x, vector_y, omitidos = _validar_y_filtrar_personas(db, matriz_x, vector_y)

    codificador = LabelEncoder()
    etiquetas = codificador.fit_transform(vector_y)

    pipeline = _crear_pipeline()

    accuracy_promedio: float | None = None
    _, conteos = np.unique(etiquetas, return_counts=True)
    minimo_por_clase = int(np.min(conteos)) if len(conteos) else 0
    pliegues_config = min(max(_SVM_PLIEGUES, 2), max(_SVM_PLIEGUES_MAX, 2))
    pliegues = min(pliegues_config, minimo_por_clase)

    if pliegues >= 2:
        estrategia_cv = StratifiedKFold(
            n_splits=pliegues,
            shuffle=True,
            random_state=_SVM_SEMILLA,
        )
        puntajes = cross_val_score(
            pipeline,
            matriz_x,
            etiquetas,
            cv=estrategia_cv,
            scoring="accuracy",
            n_jobs=-1,
        )
        accuracy_promedio = float(np.mean(puntajes))

    pipeline.fit(matriz_x, etiquetas)

    os.makedirs(_RUTA_MODELO_SVM.parent, exist_ok=True)
    artefacto = {
        "pipeline": pipeline,
        "codificador_etiquetas": codificador,
        "num_personas": int(len(codificador.classes_)),
        "dimension_embedding": int(matriz_x.shape[1]),
        "kernel": _SVM_KERNEL,
        "parametro_c": _SVM_PARAM_C,
    }
    joblib.dump(artefacto, _RUTA_MODELO_SVM)

    mensaje = "Entrenamiento completado correctamente."
    if omitidos:
        mensaje = (
            "Entrenamiento completado. Se omitieron personas con menos de 2 "
            "embeddings: "
            + ", ".join(omitidos)
        )

    return {
        "personas_entrenadas": int(len(codificador.classes_)),
        "total_embeddings": int(len(matriz_x)),
        "accuracy": accuracy_promedio,
        "modelo_guardado_en": str(_RUTA_MODELO_SVM),
        "mensaje": mensaje,
        "omitidos": omitidos,
    }