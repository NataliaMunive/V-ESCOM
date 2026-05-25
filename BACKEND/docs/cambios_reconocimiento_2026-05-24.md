# Cambios del modulo de reconocimiento facial (2026-05-24)

## Objetivo
Este documento explica, paso a paso y con nivel tecnico detallado, todos los cambios que se aplicaron en el backend de V-ESCOM para el modulo de reconocimiento facial.

Incluye:
- Que habia antes.
- Que se agrego o modifico.
- Por que se hizo.
- Que impacto tiene en produccion.
- Como probar cada cambio.

---

## 1) Estado inicial (antes de los cambios)

### 1.1 Registro e identificacion ya funcionaban
- El flujo de registro de una sola foto y la identificacion existian y estaban operativos.
- Referencias:
  - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L339)
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L101)
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L241)

### 1.2 Ya habia soporte SVM en inferencia
- El servicio podia cargar un modelo SVM desde disco y usarlo en modo auto/svm.
- Referencias:
  - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L61)
  - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L105)

### 1.3 Faltaban piezas clave para operacion diaria
- No existia endpoint API para entrenar desde panel/admin.
- No existia endpoint API para subir multiples fotos en un solo request.
- El codigo async llamaba inferencia CPU-bound de forma directa (riesgo de bloqueo del event loop).
- En despliegues multi-worker, la recarga de modelo podia quedar inconsistente por cache local por proceso.

---

## 2) Cambios funcionales principales (fase 1)

## 2.1 Nuevo servicio de entrenamiento por API

### Que se creo
- Archivo nuevo: [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py)

### Que hace internamente
1. Carga embeddings de `rostros_autorizados`.
2. Filtra personas sin suficientes muestras para entrenamiento robusto.
3. Construye pipeline de scikit-learn:
   - `Normalizer(norm='l2')`
   - `SVC(probability=True, class_weight='balanced')`
4. Ejecuta validacion cruzada cuando hay datos suficientes.
5. Entrena con todos los datos filtrados.
6. Guarda artefacto `.joblib` con:
   - `pipeline`
   - `codificador_etiquetas`
   - metadatos (`num_personas`, `dimension_embedding`, etc.)

### Funciones clave
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L33)
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L53)
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L71)
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L108)

### Por que se hizo
- Evitar depender de ejecutar scripts manuales para cada reentrenamiento.
- Permitir entrenamiento desde panel admin/API con respuesta estructurada.

---

## 2.2 Nuevo endpoint de entrenamiento

### Que se agrego
- Endpoint: `POST /reconocimiento/entrenar`
- Referencia: [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L199)

### Flujo exacto
1. Usuario admin llama endpoint.
2. Router invoca `entrenamiento_service.ejecutar_entrenamiento(db)`.
3. Se guarda el nuevo `.joblib`.
4. Se invoca `recargar_modelo_svm()` para actualizar el modelo en caliente.
5. Responde con resumen (`personas_entrenadas`, `total_embeddings`, `accuracy`, ruta del modelo).

### Beneficio
- Reentrenamiento sin reiniciar API.
- Ciclo registro -> entrenamiento -> identificacion mucho mas rapido para operacion real.

---

## 2.3 Nuevo endpoint para carga multiple de fotos

### Que se agrego
- Endpoint: `POST /reconocimiento/personas/{id_persona}/rostros`
- Referencia: [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L133)

### Comportamiento paso a paso
1. Recibe lista de archivos `imagenes`.
2. Para cada imagen:
   - Reutiliza la logica de `registrar_rostro`.
   - Si sale bien: `estado=ok`.
   - Si hay duplicado (409): `estado=duplicado` + `similitud`.
   - Si falla extraccion o validacion: `estado=error`.
3. Retorna resumen total:
   - `total_recibidas`, `exitosas`, `fallidas`, `resultados[]`.
4. Si todas fallan, retorna 422 con detalle completo del lote.

### Implementacion
- Servicio: [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L448)
- Router: [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L138)

### Beneficio
- Carga de 5-10 fotos por persona en una sola llamada.
- Menos friccion operativa para mejorar calidad del clasificador.

---

## 2.4 Nuevos esquemas de respuesta (Pydantic)

### Que se agrego
- `ResultadoEntrenamiento`
- `ResultadoImagen`
- `ResultadoSubidaMultiple`

### Referencia
- [app/schemas/reconocimiento_schema.py](../app/schemas/reconocimiento_schema.py#L67)

### Beneficio
- Contratos de respuesta claros para frontend/admin.
- Facilita renderizado de feedback por imagen en carga masiva.

---

## 2.5 Dependencias para entrenamiento

### Que se agrego
- `scikit-learn`
- `joblib`

### Referencia
- [requirements.txt](../requirements.txt#L39)

### Beneficio
- Garantiza que el entorno backend tenga librerias necesarias para entrenar/guardar modelo.

---

## 3) Cambios de rendimiento y concurrencia (fase 2)

## 3.1 Liberacion del event loop (critico)

### Problema detectado
- Endpoints `async def` estaban ejecutando inferencia pesada sincronamente.
- Riesgo: bloquear loop de FastAPI en picos de carga.

### Solucion aplicada
- Se uso `run_in_threadpool` para delegar operaciones CPU-bound.

### Dondese aplico
1. Extraccion de embedding al registrar rostro:
   - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L375)
2. Extraccion de embedding en identificacion:
   - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L570)
3. Prediccion SVM:
   - [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L608)

### Import agregado
- [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L27)

### Beneficio
- La API mantiene capacidad de atender HTTP/WebSocket concurrentes mientras se hace inferencia.

---

## 3.2 Sincronizacion de modelo entre workers por timestamp

### Problema detectado
- Con multiples workers, cada proceso tiene cache local del modelo.
- Entrenar/recargar en un proceso no actualiza automaticamente los demas.

### Solucion aplicada
- Se agrego control por `mtime` (fecha de modificacion del archivo `.joblib`).
- Antes de reutilizar cache:
  - Si el archivo en disco es nuevo, el worker invalida cache y recarga.
  - Si no cambio, mantiene cache actual.

### Implementacion
- Estado global nuevo: [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L60)
- Logica de validacion y recarga: [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L67)

### Beneficio
- Consistencia eventual automatica entre workers sin introducir Redis.

---

## 4) Cambios de resiliencia de entrenamiento (RAM y crecimiento)

## 4.1 Limites configurables para proteger memoria

### Que se agrego
- `SVM_PLIEGUES_MAX` (tope maximo de folds)
- `SVM_MAX_EMBEDDINGS` (tope de embeddings para entrenar)

### Referencia
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L31)
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L32)

### Como se usa
- Se acota query para evitar cargar volumen excesivo:
  - [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L41)
- Se acotan folds para evitar CV demasiado costosa:
  - [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py#L125)

### Beneficio
- Menor riesgo de OOM cuando crezca la BD.
- Entrenamiento mas predecible en recursos.

---

## 5) Lo que NO se rompio (compatibilidad)

- Endpoint de registro individual se mantiene:
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L101)
- Endpoint de identificar se mantiene:
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L241)
- Endpoint de estado/recarga de modelo se mantiene:
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L177)
  - [app/routes/reconocimiento.py](../app/routes/reconocimiento.py#L217)

---

## 6) Modo de identificacion (resumen tecnico)

- `auto`: intenta SVM y cae a coseno si no hay modelo.
- `svm`: exige SVM; si no hay modelo responde error.
- `coseno`: ignora SVM y usa comparacion contra BD.

Referencia de logica: [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py#L528)

---

## 7) Validacion realizada durante los cambios

Se revisaron errores en archivos modificados y no se detectaron errores estaticos:
- [app/services/reconocimiento_service.py](../app/services/reconocimiento_service.py)
- [app/services/entrenamiento_service.py](../app/services/entrenamiento_service.py)
- [app/routes/reconocimiento.py](../app/routes/reconocimiento.py)
- [app/schemas/reconocimiento_schema.py](../app/schemas/reconocimiento_schema.py)

---

## 8) Configuracion recomendada en .env

Sugerencia base para operar con seguridad:

```env
SIMILITUD_UMBRAL=0.40
RUTA_MODELO_SVM=modelos/clasificador_svm.joblib

SVM_PARAM_C=5.0
SVM_KERNEL=rbf
SVM_SEMILLA=42
SVM_PLIEGUES=5
SVM_PLIEGUES_MAX=5
SVM_MAX_EMBEDDINGS=5000
```

Ajustes practicos:
- Si hay poca RAM: bajar `SVM_MAX_EMBEDDINGS` (ej. 2000).
- Si el entrenamiento tarda demasiado: bajar `SVM_PLIEGUES` a 3.

---

## 9) Deuda tecnica abierta (no implementada aun)

Aun coexisten dos patrones de ingesta de video:
1. Pull RTSP desde backend.
2. Push HTTP desde worker externo.

Esto no se cambio todavia para evitar romper operacion actual.

Recomendacion futura:
- Estandarizar a Push HTTP desde worker externo para despliegues distribuidos.
