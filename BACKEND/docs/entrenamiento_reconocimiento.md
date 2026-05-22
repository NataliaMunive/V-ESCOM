# Entrenamiento y Enrolamiento del Sistema de Reconocimiento Facial (V-ESCOM)

Este documento explica en español cómo funciona el flujo de reconocimiento facial en este proyecto, cómo "entrenar" (enrolar) personas y cómo entrenar un clasificador supervisado sobre embeddings extraídos por InsightFace (ArcFace).

Resumen rápido:
- El sistema usa InsightFace (ArcFace) para extraer embeddings de 512 dimensiones (`extraer_embedding`).
- Los embeddings se almacenan en la BD en la tabla `rostros_autorizados` (tipo `VECTOR(512)` con `pgvector`).
- Enrolamiento = registrar varias imágenes por persona y guardar sus embeddings.
- Entrenamiento supervisado (opcional): entrenar un clasificador (p. ej. SVM) sobre los embeddings ya almacenados.

---

1) Enrolamiento (registrar personas)

- Endpoint existente para subir una foto de referencia y generar el embedding:
  - Ruta: `POST /reconocimiento/personas/{id_persona}/rostro` (ver [app/routes/reconocimiento.py](app/routes/reconocimiento.py)).
  - Acción: extrae embedding con `app.utils.face_utils.extraer_embedding`, guarda un registro en `rostros_autorizados` con `id_persona`, `embedding`, `ruta_imagen`.

- Recomendación práctica: sube varias fotos por persona (5–20) con variación en iluminación, ángulos y expresiones.

2) Registro por lote

- He incluido un script que recorre `fotos_rostros/` e inserta registros en la BD usando el mismo extractor de embeddings. Archivo: `scripts/batch_register_faces.py`.

3) Entrenamiento de un clasificador sobre embeddings (opcional pero útil)

Objetivo: usar los embeddings ya guardados para entrenar un modelo que prediga `id_persona` dados embeddings. Esto puede acelerar la inferencia cuando quieres una clasificación directa en lugar de buscar la distancia mínima en la DB.

- Ventajas:
  - Clasificadores (SVM/KNN/LogReg) pueden ser rápidos y dar probabilidad/confianza.
  - Permite evaluar la calidad de los embeddings y detectar clases con pocos ejemplos.

- Limitaciones:
  - Debes reentrenar el clasificador cuando añades nuevas personas o nuevos embeddings.
  - No cambia la red ArcFace base; sólo entrena un clasificador sobre sus salidas.

4) Script de ejemplo para entrenar un SVM (archivo incluido)

- Archivo: `scripts/train_classifier.py`
- Dependencias: `scikit-learn`, `joblib`, `numpy`. Instálalas si es necesario:

```bash
pip install scikit-learn joblib numpy
```

- Uso básico:

```bash
# desde la carpeta BACKEND con venv activado
python scripts/train_classifier.py --salida modelos/clasificador_svm.joblib
```

- Qué hace el script (resumen):
  - Conecta a la BD y extrae todas las filas de `rostros_autorizados` con embeddings.
  - Construye `X` (matriz de embeddings) y `y` (id_persona).
  - Codifica las etiquetas con `LabelEncoder` (transforma ids a 0..K-1).
  - Divide en entrenamiento/prueba (por defecto 80%/20%).
  - Entrena un `SVC` con `probability=True` (permite obtener confianza) y parámetros configurables.
  - Evalúa con `classification_report` y guarda el modelo + codificador de etiquetas en un archivo `.joblib`.

Variables y nombres en el script (explicadas):

- `db`: sesión de SQLAlchemy (`SessionLocal`).
- `filas`: lista de objetos `RostroAutorizado` obtenidos de la BD.
- `X`: matriz NumPy (n_muestras, 512) con embeddings.
- `y`: vector de etiquetas original (id_persona entero).
- `codificador_etiquetas` (`LabelEncoder`): transforma `y` a `y_enc` (enteros secuenciales).
- `X_train, X_test, y_train, y_test`: split de datos.
- `clasificador`: instancia de `sklearn.svm.SVC` entrenada sobre `X_train`.

5) Recomendaciones prácticas y ajustes

- Si agregas nuevas personas, ejecuta nuevamente el script para reentrenar el clasificador.
- Ajusta `SIMILITUD_UMBRAL` en `.env` si usas búsqueda por distancia (valor por defecto: `0.40`).
- Para mayor robustez, guarda múltiples embeddings por persona y, al identificar, promedia probabilidades o usa reglas de votación.

6) Privacidad y consideraciones éticas

- Asegura consentimiento explícito para almacenar fotos y datos biométricos.
- Restringe acceso a la base de datos y backups.

---

Si quieres, puedo:
- Ejecutar el entrenamiento aquí si confirmas que la BD y el entorno virtual están activos.
- Generar un endpoint que cargue el clasificador y devuelva la predicción con confianza.

FIN
