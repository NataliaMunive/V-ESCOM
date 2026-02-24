-- =====================================================
-- Base de datos
-- V-ESCOM (script principal único)
-- PostgreSQL
-- =====================================================

BEGIN;

-- -----------------------------------------------------
-- Extensiones
-- -----------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------
-- Catálogos y administración
-- -----------------------------------------------------

CREATE TABLE cubiculos (
    id_cubiculo SERIAL PRIMARY KEY,
    numero_cubiculo VARCHAR(20) NOT NULL UNIQUE,
    capacidad INT NOT NULL,
    responsable VARCHAR(100)
);

CREATE TABLE administradores (
    id_admin SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    fotografia VARCHAR(255),
    contrasena VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    intentos_fallidos INT NOT NULL DEFAULT 0,
    bloqueado_hasta TIMESTAMP NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE camaras (
    id_camara SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    direccion_ip VARCHAR(45),
    ubicacion VARCHAR(100),
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    estado VARCHAR(20) NOT NULL DEFAULT 'Activa',
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_estado_camara CHECK (estado IN ('Activa', 'Inactiva', 'Error'))
);

CREATE TABLE profesores (
    id_profesor SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------
-- Reconocimiento facial
-- -----------------------------------------------------

CREATE TABLE personas_autorizadas (
    id_persona SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100),
    telefono VARCHAR(20),
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    rol VARCHAR(30) NOT NULL DEFAULT 'Profesor',
    ruta_rostro VARCHAR(255),
    embedding BYTEA,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE personas_no_autorizadas (
    id_pna SERIAL PRIMARY KEY,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME,
    ruta_imagen_captura VARCHAR(255),
    embedding_detectado BYTEA
);

CREATE TABLE embeddings (
    id_embedding SERIAL PRIMARY KEY,
    id_persona INT UNIQUE REFERENCES personas_autorizadas(id_persona) ON DELETE CASCADE,
    vector BYTEA NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Entidad del ER: Entrada
CREATE TABLE entradas (
    id_entrada SERIAL PRIMARY KEY,
    id_camara INT REFERENCES camaras(id_camara),
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    nombre VARCHAR(100),
    tipo VARCHAR(30),
    estado VARCHAR(20) DEFAULT 'Activa'
);

-- -----------------------------------------------------
-- Operación, alertas, notificaciones y logs
-- -----------------------------------------------------

CREATE TABLE eventos_acceso (
    id_evento SERIAL PRIMARY KEY,
    id_camara INT REFERENCES camaras(id_camara),
    id_persona INT REFERENCES personas_autorizadas(id_persona),
    tipo_acceso VARCHAR(20) NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME,
    similitud FLOAT,
    CONSTRAINT chk_tipo_acceso CHECK (tipo_acceso IN ('Autorizado', 'No Autorizado'))
);

CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    id_evento INT REFERENCES eventos_acceso(id_evento),
    tipo_alerta VARCHAR(50) NOT NULL DEFAULT 'Intrusion',
    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME
);

CREATE TABLE notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_alerta INT REFERENCES alertas(id_alerta),
    destinatario VARCHAR(100),
    telefono VARCHAR(20),
    medio VARCHAR(20),
    estado VARCHAR(20),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME
);

CREATE TABLE logs_sistema (
    id_log SERIAL PRIMARY KEY,
    id_evento INT REFERENCES eventos_acceso(id_evento),
    tipo VARCHAR(30),
    nivel VARCHAR(20),
    origen VARCHAR(50),
    mensaje TEXT,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;