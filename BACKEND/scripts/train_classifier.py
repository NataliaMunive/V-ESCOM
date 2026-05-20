"""Entrena un clasificador (SVM) usando los embeddings guardados en la BD.

Uso:
  desde la carpeta BACKEND con el entorno virtual activo:
    python scripts/train_classifier.py --salida modelos/clasificador_svm.joblib

El script extrae todas las filas de `rostros_autorizados`, construye X e y,
entrena un SVM y guarda el artefacto con Joblib.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import classification_report
import joblib

from app.bd import SessionLocal
from app.models.rostro_autorizado import RostroAutorizado


def cargar_embeddings_desde_bd():
    """Devuelve (X, y) donde X es array (n,512) y y vector de ids de persona."""
    db = SessionLocal()
    try:
        filas = (
            db.query(RostroAutorizado)
            .filter(RostroAutorizado.embedding.isnot(None))
            .all()
        )
        if not filas:
            raise RuntimeError("No se encontraron embeddings en la base de datos.")

        X = np.array([np.array(f.embedding, dtype=np.float32) for f in filas], dtype=np.float32)
        y = np.array([int(f.id_persona) for f in filas], dtype=np.int32)
        return X, y
    finally:
        db.close()


def entrenar_clasificador(
    X: np.ndarray,
    y: np.ndarray,
    salida_path: Path,
    test_size: float = 0.2,
    C: float = 1.0,
    kernel: str = "linear",
    random_state: int = 42,
) -> Any:
    """Entrena un SVC y guarda el modelo + codificador de etiquetas en `salida_path`."""
    # Codificar etiquetas (id_persona -> 0..K-1)
    codificador_etiquetas = LabelEncoder()
    y_enc = codificador_etiquetas.fit_transform(y)

    # División entrenamiento / prueba
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=test_size, stratify=y_enc, random_state=random_state
    )

    # Crear el clasificador SVM
    clasificador = SVC(C=C, kernel=kernel, probability=True, random_state=random_state)
    clasificador.fit(X_train, y_train)

    # Evaluación
    y_pred = clasificador.predict(X_test)
    informe = classification_report(y_test, y_pred, zero_division=0)

    # Guardar artefactos: modelo + codificador
    os.makedirs(salida_path.parent, exist_ok=True)
    joblib.dump({"modelo": clasificador, "codificador": codificador_etiquetas}, salida_path)

    return informe


def main():
    parser = argparse.ArgumentParser(description="Entrena clasificador sobre embeddings")
    parser.add_argument("--salida", required=True, help="Ruta de salida .joblib para el modelo")
    parser.add_argument("--test-size", type=float, default=0.2, help="Proporción para test (por defecto 0.2)")
    parser.add_argument("--C", type=float, default=1.0, help="Parámetro C del SVM (por defecto 1.0)")
    parser.add_argument("--kernel", type=str, default="linear", help="Kernel SVM (linear, rbf...)")
    args = parser.parse_args()

    salida = Path(args.salida)

    print("Cargando embeddings desde la BD...")
    X, y = cargar_embeddings_desde_bd()
    print(f"Embeddings cargados: {X.shape[0]} muestras, dimensión {X.shape[1]}")

    print("Entrenando clasificador SVM...")
    informe = entrenar_clasificador(
        X,
        y,
        salida_path=salida,
        test_size=args.test_size,
        C=args.C,
        kernel=args.kernel,
    )

    print("Evaluación del clasificador (test):")
    print(informe)
    print(f"Modelo guardado en: {salida}")


if __name__ == "__main__":
    main()
