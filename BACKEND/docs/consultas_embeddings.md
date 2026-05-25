# Consultas útiles para embeddings (pgAdmin/Postgres)

Este documento reúne consultas SQL para inspeccionar, depurar y exportar los embeddings almacenados en la tabla `rostros_autorizados` (campo `embedding` de tipo `VECTOR(512)`). Ejecuta estas consultas desde el Query Tool de pgAdmin o psql.

---

## 1) Cantidad de embeddings por persona

```sql
SELECT
  id_persona,
  COUNT(*) AS total_embeddings
FROM rostros_autorizados
GROUP BY id_persona
ORDER BY total_embeddings DESC;
```

## 2) Ver embeddings "puros" (vector completo como texto)

```sql
SELECT
  id_rostro,
  id_persona,
  embedding::text AS embedding_puro
FROM rostros_autorizados
ORDER BY id_rostro DESC;
```

## 3) Preview del embedding (solo primeros caracteres)

```sql
SELECT
  id_rostro,
  id_persona,
  substring(embedding::text from 1 for 300) AS preview_embedding,
  fecha_captura
FROM rostros_autorizados
ORDER BY id_rostro DESC;
```

## 4) Detectar embeddings nulos o con dimensión inesperada

```sql
SELECT
  id_rostro,
  id_persona,
  embedding IS NULL AS es_null,
  array_length(embedding::real[], 1) AS dimension
FROM rostros_autorizados
ORDER BY id_rostro DESC;
```

## 5) Similitud coseno entre dos embeddings (misma persona)

```sql
SELECT
  a.id_rostro AS rostro_1,
  b.id_rostro AS rostro_2,
  1 - (a.embedding <=> b.embedding) AS similitud_coseno
FROM rostros_autorizados a
JOIN rostros_autorizados b
  ON a.id_persona = b.id_persona
 AND a.id_rostro < b.id_rostro
ORDER BY similitud_coseno DESC;
```

## 6) Lista con persona, conteo de embeddings y preview

```sql
SELECT
  r.id_rostro,
  r.id_persona,
  p.nombre,
  p.apellidos,
  COUNT(*) OVER (PARTITION BY r.id_persona) AS total_embeddings_persona,
  substring(r.embedding::text from 1 for 300) AS preview_embedding,
  r.fecha_captura
FROM rostros_autorizados r
JOIN personas_autorizadas p
  ON p.id_persona = r.id_persona
ORDER BY r.id_rostro DESC;
```

## 7) Agrupar por persona (resumen)

```sql
SELECT
  p.id_persona,
  p.nombre,
  p.apellidos,
  COUNT(r.id_rostro) AS total_embeddings,
  string_agg(r.id_rostro::text, ', ' ORDER BY r.id_rostro DESC) AS ids_rostros
FROM personas_autorizadas p
LEFT JOIN rostros_autorizados r
  ON r.id_persona = p.id_persona
GROUP BY p.id_persona, p.nombre, p.apellidos
ORDER BY total_embeddings DESC, p.id_persona;
```

## 8) Extraer un embedding específico como CSV (exportable)

```sql
-- Reemplaza 1 por el id_rostro deseado
COPY (
  SELECT id_rostro, id_persona, embedding::text AS embedding_puro
  FROM rostros_autorizados
  WHERE id_rostro = 1
) TO STDOUT WITH CSV HEADER;
```

Si usas pgAdmin: ejecuta la consulta y usa el botón de exportar resultados a CSV.

---

Si quieres, añado una consulta para comparar un embedding externo (valor) con la tabla y obtener las top-N coincidencias. 
