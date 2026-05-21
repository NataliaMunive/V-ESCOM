"""Entrena un clasificador SVM usando los embeddings guardados en la BD.

Uso (desde la carpeta BACKEND con el entorno virtual activo):
  python entrenamiento/entrenar_clasificador.py --salida modelos/clasificador_svm.joblib

El script:
  1. Carga todos los embeddings de `rostros_autorizados`
  2. Valida que cada persona tenga al menos 2 imágenes (requerido por stratify)
  3. Normaliza los vectores (mejora el rendimiento con kernel rbf)
  4. Construye un Pipeline: Normalizador → SVC(rbf)
  5. Evalúa con Validación Cruzada Estratificada (CV=5)
  6. Re-entrena con TODOS los datos y guarda el modelo + codificador de etiquetas

Mejoras aplicadas vs. versión anterior:
  - Kernel rbf por defecto (mejor para 10–50 personas)
  - Normalización L2 de embeddings dentro del Pipeline
  - Validación cruzada estratificada (CV=5) en lugar de un solo split
  - Validación previa: detecta personas con < 2 imágenes
  - Nombres de variables y funciones en español
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, Normalizer
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report
import joblib

from app.bd import SessionLocal
from app.models.rostro_autorizado import RostroAutorizado

# Número de particiones para la validación cruzada
NUM_PARTICIONES_CV = 5


def cargar_embeddings_desde_bd() -> tuple[np.ndarray, np.ndarray]:
    """Carga todos los embeddings y sus etiquetas desde la base de datos.

    Devuelve:
        X : array de forma (n_muestras, dimensión_embedding)
        y : array de ids de persona (int32)
    """
    sesion_bd = SessionLocal()
    try:
        filas = (
            sesion_bd.query(RostroAutorizado)
            .filter(RostroAutorizado.embedding.isnot(None))
            .all()
        )
        if not filas:
            raise RuntimeError(
                "No se encontraron embeddings en la base de datos. "
                "Ejecuta primero registrar_rostros_lote.py."
            )

        matriz_x = np.array(
            [np.array(fila.embedding, dtype=np.float32) for fila in filas],
            dtype=np.float32,
        )
        vector_y = np.array([int(fila.id_persona) for fila in filas], dtype=np.int32)
        return matriz_x, vector_y
    finally:
        sesion_bd.close()


def validar_minimo_muestras(vector_y: np.ndarray, minimo: int = 2) -> None:
    """Verifica que cada persona tenga al menos `minimo` imágenes.

    Si alguna persona tiene menos muestras de las requeridas por la
    validación cruzada estratificada, lanza un RuntimeError con detalle.
    """
    clases, conteos = np.unique(vector_y, return_counts=True)
    personas_insuficientes = clases[conteos < minimo]

    if len(personas_insuficientes) > 0:
        detalle = ", ".join(
            f"id={pid} ({conteos[clases == pid][0]} img)"
            for pid in personas_insuficientes
        )
        raise RuntimeError(
            f"Las siguientes personas tienen menos de {minimo} imágenes "
            f"(requeridas para CV estratificado): {detalle}. "
            f"Agrega más fotos o usa --pliegues 2."
        )


def construir_pipeline(parametro_c: float, kernel: str, semilla: int) -> Pipeline:
    """Construye el Pipeline: Normalizador L2 → SVC.

    La normalización L2 es especialmente importante con kernel 'rbf'
    ya que hace que las distancias euclidianas sean equivalentes a la
    similitud coseno.
    """
    return Pipeline([
        ('normalizador', Normalizer(norm='l2')),
        ('clasificador', SVC(
            C=parametro_c,
            kernel=kernel,
            probability=True,
            random_state=semilla,
            class_weight='balanced',   # maneja clases desbalanceadas
        )),
    ])


def evaluar_con_validacion_cruzada(
    pipeline: Pipeline,
    matriz_x: np.ndarray,
    etiquetas_enc: np.ndarray,
    num_pliegues: int,
    semilla: int,
) -> None:
    """Ejecuta CV estratificado e imprime exactitud media y desviación."""
    estrategia_cv = StratifiedKFold(
        n_splits=num_pliegues,
        shuffle=True,
        random_state=semilla,
    )
    puntuaciones = cross_val_score(
        pipeline, matriz_x, etiquetas_enc,
        cv=estrategia_cv,
        scoring='accuracy',
        n_jobs=-1,   # usa todos los núcleos disponibles
    )
    print(f"\n  Validación Cruzada (CV={num_pliegues}):")
    print(f"    Exactitud por pliegue : {np.round(puntuaciones, 4)}")
    print(f"    Media ± Desv. estándar: {puntuaciones.mean():.4f} ± {puntuaciones.std():.4f}")


def entrenar_y_guardar(
    matriz_x: np.ndarray,
    vector_y: np.ndarray,
    ruta_salida: Path,
    parametro_c: float,
    kernel: str,
    num_pliegues: int,
    semilla: int,
) -> None:
    """Entrena el pipeline con TODOS los datos y guarda el artefacto .joblib."""

    # ── 1. Codificar etiquetas (id_persona → 0..K-1) ─────────────────────────
    codificador_etiquetas = LabelEncoder()
    etiquetas_enc = codificador_etiquetas.fit_transform(vector_y)

    num_personas = len(codificador_etiquetas.classes_)
    print(f"\n  Personas detectadas : {num_personas}")
    print(f"  Total de muestras   : {len(matriz_x)}")
    print(f"  Dimensión embedding : {matriz_x.shape[1]}")

    # ── 2. Construir el Pipeline ──────────────────────────────────────────────
    pipeline = construir_pipeline(parametro_c, kernel, semilla)

    # ── 3. Validación cruzada para medir rendimiento ──────────────────────────
    print("\nEvaluando con Validación Cruzada Estratificada...")
    evaluar_con_validacion_cruzada(pipeline, matriz_x, etiquetas_enc, num_pliegues, semilla)

    # ── 4. Entrenamiento final con TODOS los datos ────────────────────────────
    print("\nEntrenando modelo final con todos los datos...")
    pipeline.fit(matriz_x, etiquetas_enc)

    # Reporte breve sobre datos de entrenamiento completos
    etiquetas_predichas = pipeline.predict(matriz_x)
    print("\n  Reporte sobre datos de entrenamiento completo (referencia):")
    informe = classification_report(
        etiquetas_enc, etiquetas_predichas,
        target_names=[str(c) for c in codificador_etiquetas.classes_],
        zero_division=0,
    )
    print(informe)

    # ── 5. Guardar modelo + codificador ──────────────────────────────────────
    os.makedirs(ruta_salida.parent, exist_ok=True)
    artefacto = {
        "pipeline": pipeline,
        "codificador_etiquetas": codificador_etiquetas,
        "num_personas": num_personas,
        "dimension_embedding": matriz_x.shape[1],
        "kernel": kernel,
        "parametro_c": parametro_c,
    }
    joblib.dump(artefacto, ruta_salida)
    print(f"\n  Modelo guardado en: {ruta_salida}")


def main():
    analizador = argparse.ArgumentParser(
        description="Entrena un clasificador SVM (rbf) sobre embeddings faciales."
    )
    analizador.add_argument(
        "--salida", required=True,
        help="Ruta de salida del modelo .joblib (ej. modelos/clasificador_svm.joblib)"
    )
    analizador.add_argument(
        "--C", type=float, default=5.0,
        help="Parámetro de regularización C del SVM (por defecto 5.0)"
    )
    analizador.add_argument(
        "--kernel", type=str, default="rbf",
        choices=["rbf", "linear", "poly"],
        help="Kernel del SVM: rbf (por defecto), linear, poly"
    )
    analizador.add_argument(
        "--pliegues", type=int, default=NUM_PARTICIONES_CV,
        help=f"Número de pliegues para Validación Cruzada (por defecto {NUM_PARTICIONES_CV})"
    )
    analizador.add_argument(
        "--semilla", type=int, default=42,
        help="Semilla aleatoria para reproducibilidad (por defecto 42)"
    )
    argumentos = analizador.parse_args()

    ruta_salida = Path(argumentos.salida)

    print("=" * 55)
    print("  ENTRENAMIENTO DE CLASIFICADOR DE ROSTROS (SVM)")
    print("=" * 55)

    # ── Cargar datos ──────────────────────────────────────────────────────────
    print("\nCargando embeddings desde la base de datos...")
    matriz_x, vector_y = cargar_embeddings_desde_bd()

    # ── Validar mínimo de muestras por clase ──────────────────────────────────
    print("Validando mínimo de imágenes por persona...")
    validar_minimo_muestras(vector_y, minimo=argumentos.pliegues)
    print("  ✓ Validación superada.")

    # ── Entrenar y guardar ────────────────────────────────────────────────────
    entrenar_y_guardar(
        matriz_x=matriz_x,
        vector_y=vector_y,
        ruta_salida=ruta_salida,
        parametro_c=argumentos.C,
        kernel=argumentos.kernel,
        num_pliegues=argumentos.pliegues,
        semilla=argumentos.semilla,
    )

    print("\n¡Entrenamiento completado exitosamente!")
    print("=" * 55)


if __name__ == "__main__":
    main()
