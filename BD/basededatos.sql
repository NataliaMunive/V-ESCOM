-- Base de datos
-- V-ESCOM

-- -----------------------------------------------------
-- Extensiones necesarias: pgvector para los embeddings y pgcrypto para seguridad
-- -----------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------
-- Catalogos: cubiculos, administrador, camaras
-- -----------------------------------------------------

CREATE TABLE cubiculos (
    id_cubiculo SERIAL PRIMARY KEY,
    numero_cubiculo VARCHAR(20) NOT NULL UNIQUE, 
    capacidad INT NOT NULL,
    responsable VARCHAR(100) -- Nombre del profesor titular
);

CREATE TABLE administradores (
    id_admin SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    fotografia VARCHAR(255), -- Ruta relativa de la imagen
    contrasena VARCHAR(255) NOT NULL, -- Guardar hash, no texto plano
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE camaras (
    id_camara SERIAL PRIMARY KEY,
    nombre_camara VARCHAR(50),
    direccion_ip VARCHAR(45) NOT NULL,
    ubicacion VARCHAR(100), -- Descripcion del lugar
    estado VARCHAR(20) DEFAULT 'Activa' -- 'Activa', 'Inactiva', 'Error'
);

-- -----------------------------------------------------
-- Tablas principales de usuarios
-- -----------------------------------------------------

CREATE TABLE personas_autorizadas (
    id_persona SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100),
    telefono VARCHAR(20),
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    rol VARCHAR(30) DEFAULT 'Profesor',
    ruta_rostro VARCHAR(255), 
    embedding vector(512), -- Vector generado por ArcFace
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE personas_no_autorizadas (
    id_pna SERIAL PRIMARY KEY,
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME,
    ruta_imagen_captura VARCHAR(255), -- Foto capturada al momento de la alerta
    embedding_detectado vector(512) -- Para detectar reincidencia
);

-- -----------------------------------------------------
-- Operacion y logs
-- -----------------------------------------------------

CREATE TABLE eventos_acceso (
    id_evento SERIAL PRIMARY KEY,
    id_camara INT REFERENCES camaras(id_camara),
    id_persona INT REFERENCES personas_autorizadas(id_persona), -- Null si es desconocido
    tipo_acceso VARCHAR(20), -- Autorizado / No Autorizado
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME,
    similitud FLOAT -- Valor de confianza (0.0 a 1.0)
);

CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    id_evento INT REFERENCES eventos_acceso(id_evento),
    tipo_alerta VARCHAR(50) DEFAULT 'Intrusion',
    estado VARCHAR(20) DEFAULT 'Pendiente', -- 'Pendiente', 'Enviada', 'Revisada'
    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_alerta INT REFERENCES alertas(id_alerta),
    destinatario VARCHAR(100),
    medio VARCHAR(20), -- SMS
    estado VARCHAR(20), -- 'Enviado', 'Fallido'
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logs_sistema (
    id_log SERIAL PRIMARY KEY,
    nivel VARCHAR(20), -- INFO, ERROR, WARN
    origen VARCHAR(50), 
    mensaje TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);