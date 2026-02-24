# V-ESCOM - Sistema de Vigilancia con Reconocimiento Facial

## Descripción General

**V-ESCOM** es un sistema de vigilancia inteligente para cubículos en ESCOM-IPN que utiliza reconocimiento facial para controlar el acceso y registrar eventos de entrada/salida. El sistema identifica automáticamente a personas autorizadas mediante embeddings de IA (ArcFace) y genera alertas para accesos no autorizados.

## Características Principales

- ✅ **Autenticación JWT**: Login seguro de administradores con hash bcrypt y bloqueo temporal tras fallos.
- ✅ **Reconocimiento Facial**: Detección y extracción de embeddings con InsightFace (ArcFace R100).
- ✅ **Gestión de Usuarios**: CRUD completo para profesores, personas autorizadas y administradores.
- ✅ **Control de Cámaras**: Registro de cámaras IP con ubicación y estado.
- ✅ **Historial de Eventos**: Seguimiento de accesos (autorizado/no autorizado) con similitud.
- ✅ **Sistema de Alertas**: Generación de alertas y notificaciones para accesos sospechosos.
- ✅ **Auditoría**: Logs de sistema para trazabilidad completa.

## Stack Técnico

| Componente     | Tecnología                                    |
|----------------|-----------------------------------------------|
| **Framework**  | FastAPI + Uvicorn                             |
| **ORM/Base de datos** | SQLAlchemy + PostgreSQL                       |
| **Reconocimiento facial** | InsightFace (ArcFace) + OpenCV + NumPy        |
| **Autenticación**       | JWT (python-jose) + Bcrypt                    |
| **Validación**  | Pydantic v2                                   |
| **API Docs**   | Swagger UI (automático en /docs)              |

## Estructura del Proyecto

```
V-ESCOM/
├── BACKEND/                    # Código del servidor
│   ├── app/
│   │   ├── main.py            # Aplicación FastAPI principal
│   │   ├── bd.py              # Conexión a BD
│   │   ├── models/            # Modelos SQLAlchemy (ORM)
│   │   │   ├── administrador.py
│   │   │   ├── profesor.py
│   │   │   ├── camara.py
│   │   │   ├── persona_autorizada.py
│   │   │   ├── evento.py
│   │   │   ├── alerta.py
│   │   │   ├── notificacion.py
│   │   │   ├── log_sistema.py
│   │   │   ├── entrada.py
│   │   │   ├── cubiculo.py
│   │   │   └── embedding.py
│   │   ├── schemas/           # Schemas Pydantic (DTO)
│   │   │   ├── auth_schema.py
│   │   │   ├── profesor_schema.py
│   │   │   ├── camara_schema.py
│   │   │   └── reconocimiento_schema.py
│   │   ├── services/          # Lógica de negocio
│   │   │   ├── auth_service.py
│   │   │   ├── profesor_service.py
│   │   │   ├── camara_service.py
│   │   │   └── reconocimiento_service.py
│   │   ├── routes/            # Endpoints (routers)
│   │   │   ├── auth.py
│   │   │   ├── profesores.py
│   │   │   ├── camaras.py
│   │   │   └── reconocimiento.py
│   │   ├── core/              # Infraestructura
│   │   │   ├── security.py    # JWT, hashing
│   │   │   └── deps.py        # Dependencias (autenticación)
│   │   └── utils/
│   │       └── face_utils.py  # Utilidades de reconocimiento facial
│   └── requirements.txt       # Dependencias de Python
├── BD/
│   └── basededatos.sql        # Script SQL para crear tablas
├── .env.example               # Variables de entorno de ejemplo
├── .gitignore                 # Archivos a ignorar en git
└── README.md                  # Este archivo
```

## Instalación y Setup

### 1. Requisitos Previos

- Python 3.10+
- PostgreSQL 12+
- Git

### 2. Clonar o Descargar el Código

```bash
git clone <tu-repo>
cd V-ESCOM
```

### 3. Crear Entorno Virtual

```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Linux/MacOS:
source venv/bin/activate
```

### 4. Instalar Dependencias

```bash
cd BACKEND
pip install -r requirements.txt
```

### 5. Configurar Base de Datos

a) **Crear base de datos en PostgreSQL:**
```sql
CREATE DATABASE vescom;
```

b) **Ejecutar script SQL** (desde conexión a `vescom`):
```bash
psql -U postgres -d vescom -f ../BD/basededatos.sql
```

### 6. Configurar Variables de Entorno

Copiar `.env.example` a `.env` y llenar con valores reales:
```bash
cp .env.example .env
```

Editar `.env`:
```dotenv
DATABASE_URL=postgresql://postgres:tu_contraseña@localhost/vescom
SECRET_KEY=una_cadena_aleatoria_muy_segura_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=60
SIMILITUD_UMBRAL=0.40
DEBUG=False
```

> ⚠️ **Importante**: Nunca subir `.env` a git. Usar solo `.env.example`.

### 7. Verificar Setup

```bash
# Desde BACKEND/
python -c "from app.bd import engine; engine.connect(); print('BD OK')"
```

## Uso: Iniciar el Servidor

```bash
cd BACKEND
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará en: **http://localhost:8000**

### Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints Principales

### Autenticación

| Método | Endpoint             | Descripción                          |
|--------|----------------------|--------------------------------------|
| POST   | `/auth/login`        | Login de administrador (retorna JWT) |
| POST   | `/auth/admins`       | Crear administrador (protegido)      |
| GET    | `/auth/admins`       | Listar administradores (protegido)   |
| GET    | `/auth/admins/me`    | Perfil del admin actual (protegido)  |

### Profesores

| Método | Endpoint                | Descripción                      |
|--------|-------------------------|----------------------------------|
| POST   | `/profesores`           | Crear profesor (protegido)       |
| GET    | `/profesores`           | Listar profesores (protegido)    |
| GET    | `/profesores/id_profesor` | Obtener profesor por ID (protegido) |
| PUT    | `/profesores/id_profesor` | Actualizar profesor (protegido)  |
| DELETE | `/profesores/id_profesor` | Desactivar profesor (protegido)  |

### Cámaras

| Método | Endpoint             | Descripción                    |
|--------|----------------------|--------------------------------|
| POST   | `/camaras`           | Crear cámara (protegido)       |
| GET    | `/camaras`           | Listar cámaras (protegido)     |
| GET    | `/camaras/id_camara` | Obtener cámara por ID (protegido) |
| PUT    | `/camaras/id_camara` | Actualizar cámara (protegido)  |
| DELETE | `/camaras/id_camara` | Desactivar cámara (protegido)  |

### Reconocimiento Facial

| Método | Endpoint                          | Descripción                                      |
|--------|-----------------------------------|--------------------------------------------------|
| POST   | `/reconocimiento/personas`        | Registrar persona autorizada (protegido)         |
| GET    | `/reconocimiento/personas`        | Listar personas autorizadas (protegido)          |
| POST   | `/reconocimiento/personas/{id}/rostro` | Subir foto y generar embedding (protegido) |
| POST   | `/reconocimiento/identificar`     | Identificar rostro en imagen (protegido)         |
| GET    | `/reconocimiento/eventos`         | Listar eventos de acceso (protegido)             |

## Flujo de Ejemplo: Identificación Facial

1. **Admin registra persona autorizada**:
   ```
   POST /reconocimiento/personas
   {
     "nombre": "Juan",
     "apellidos": "Pérez",
     "email": "juan.perez@escom.ipn.mx",
     "id_cubiculo": 1,
     "rol": "Profesor"
   }
   ```

2. **Admin sube foto de referencia**:
   ```
   POST /reconocimiento/personas/1/rostro
   [multipart: archivo imagen JPEG/PNG]
   ```
   → Se extrae embedding ArcFace y se almacena.

3. **Cámara envía frame capturado**:
   ```
   POST /reconocimiento/identificar
   [multipart: frame, id_camara=1]
   ```

4. **Sistema responde**:
   ```json
   {
     "tipo_acceso": "Autorizado",
     "similitud": 0.92,
     "id_persona": 1,
     "nombre": "Juan",
     "apellidos": "Pérez",
     "id_evento": 42
   }
   ```

5. **Evento registrado** en `eventos_acceso` para auditoría.

## Autenticación

Todos los endpoints (excepto `/auth/login`) requieren un **Bearer Token JWT** en el header:

```
Authorization: Bearer <token_aqui>
```

### Ejemplo de Login:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=tu_contraseña"
```

Respuesta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Base de Datos: Entidades Principales

| Tabla                      | Descripción                                         |
|---------------------------|-----------------------------------------------------|
| `administradores`          | Usuarios del sistema (admin con login JWT)          |
| `cubiculos`                | Cubículos/salas a vigilar                           |
| `camaras`                  | Cámaras IP con ubicación y estado                   |
| `profesores`               | Profesores (referencia de ocupantes)                |
| `personas_autorizadas`     | Personas registradas con rostro y embedding         |
| `personas_no_autorizadas`  | Rostros detectados no identificados                 |
| `embeddings`               | Vectores ArcFace (512-d) de personas autorizadas    |
| `eventos_acceso`           | Historial de intentos de acceso (autorizado/no)     |
| `alertas`                  | Alertas generadas por accesos sospechosos           |
| `notificaciones`           | Notificaciones enviadas (SMS, email, etc.)          |
| `logs_sistema`             | Auditoría de operaciones del sistema                |
| `entradas`                 | Puntos de entrada (puertas) por cubiculo            |

## Variables de Entorno

| Variable                   | Ejemplo                                    | Descripción                          |
|----------------------------|--------------------------------------------|--------------------------------------|
| `DATABASE_URL`             | `postgresql://user:pass@localhost/vescom`  | Conexión a PostgreSQL                |
| `SECRET_KEY`               | Una cadena aleatoria larga y fuerte        | Clave para firmar JWT                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                                    | Expiración del token en minutos       |
| `SIMILITUD_UMBRAL`         | `0.40`                                     | Umbral ArcFace para identificación   |
| `DEBUG`                    | `False`                                    | Modo debug (False en producción)     |

## Seguridad

- ✅ **Contraseñas**: Hash bcrypt, nunca almacenadas en texto plano.
- ✅ **JWT**: Firmado con HS256, configurable en `.env`.
- ✅ **Bloqueo de cuenta**: 3 intentos fallidos → bloqueo 5 minutos.
- ✅ **CORS**: Configurable en `app/main.py` (actualmente `*`, cambiar en producción).
- ✅ **BYTEA para embeddings**: Binario serializado, sin dependencia de `pgvector`.

## Troubleshooting

### Error: "No module named app"

Asegúrate de estar en la carpeta `BACKEND/` cuando ejecutes el servidor.

### Error: "relation \"administradores\" does not exist"

Ejecuta el script SQL en la BD:
```bash
psql -U postgres -d vescom -f ../BD/basededatos.sql
```

### Error al conectar a PostgreSQL

Verifica que:
1. PostgreSQL esté corriendo.
2. Las credenciales en `.env` sean correctas.
3. La BD `vescom` exista.

### InsightFace descargando modelos

La primera ejecución descargará modelos (~1GB). Es normal y tarda unos minutos. Los modelos se cachean en `~/.insightface/`.

## Próximas Mejoras

- [ ] Frontend web (React/Vue) para admin dashboard.
- [ ] Mobile app para consultar alertas en tiempo real.
- [ ] Webhook para integración con sistemas de notificación.
- [ ] Soporte para múltiples tipos de biometría.
- [ ] Machine Learning para detección de anomalías.

## Contribuciones

1. Fork el repo.
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`.
3. Commits con mensaje claro: `git commit -m "Agregar nueva funcionalidad"`.
4. Push: `git push origin feature/nueva-funcionalidad`.
5. Abre un Pull Request.

## Licencia

Este proyecto es parte de ESCOM-IPN. Contactar con los administradores para permisos de uso.

## Contacto y Soporte

- **Email**: [tu-email@escom.ipn.mx](mailto:tu-email@escom.ipn.mx)
- **Issues**: Reportar problemas en la sección Issues.

---

**Última actualización**: Febrero 2026 | **Versión**: 1.0.0
