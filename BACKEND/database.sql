-- =====================================================
-- V-ESCOM: Script de Base de Datos
-- PostgreSQL 18 + pgvector
-- =====================================================

-- Extensiones
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------
-- Tablas de catálogos
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS cubiculos (
    id_cubiculo SERIAL PRIMARY KEY,
    numero_cubiculo VARCHAR(20) NOT NULL UNIQUE, 
    capacidad INT NOT NULL,
    responsable VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS administradores (
    id_admin SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    fotografia VARCHAR(255),
    contrasena VARCHAR(255) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    intentos_fallidos INTEGER DEFAULT 0,
    bloqueado_hasta TIMESTAMP,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS camaras (
    id_camara SERIAL PRIMARY KEY,
    nombre VARCHAR(50),
    direccion_ip VARCHAR(45),
    ubicacion VARCHAR(100),
    id_cubiculo INTEGER REFERENCES cubiculos(id_cubiculo),
    activa BOOLEAN DEFAULT TRUE,
    estado VARCHAR(20) DEFAULT 'Activa',
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------------
-- Tablas principales de usuarios
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS personas_autorizadas (
    id_persona SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(100),
    telefono VARCHAR(20),
    id_cubiculo INT REFERENCES cubiculos(id_cubiculo),
    rol VARCHAR(30) DEFAULT 'Profesor',
    ruta_rostro VARCHAR(255), 
    embedding vector(512),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personas_no_autorizadas (
    id_pna SERIAL PRIMARY KEY,
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME,
    ruta_imagen_captura VARCHAR(255),
    embedding_detectado vector(512)
);

-- -----------------------------------------------------
-- Operación y logs
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS eventos_acceso (
    id_evento SERIAL PRIMARY KEY,
    id_camara INT REFERENCES camaras(id_camara),
    id_persona INT REFERENCES personas_autorizadas(id_persona),
    tipo_acceso VARCHAR(20),
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME,
    similitud FLOAT
);

CREATE TABLE IF NOT EXISTS alertas (
    id_alerta SERIAL PRIMARY KEY,
    id_evento INT REFERENCES eventos_acceso(id_evento),
    tipo_alerta VARCHAR(50) DEFAULT 'Intrusion',
    estado VARCHAR(20) DEFAULT 'Pendiente',
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_alerta INT REFERENCES alertas(id_alerta),
    destinatario VARCHAR(100),
    medio VARCHAR(20),
    estado VARCHAR(20),
    telefono VARCHAR(20),
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME
);

CREATE TABLE IF NOT EXISTS logs_sistema (
    id_log SERIAL PRIMARY KEY,
    id_evento INTEGER REFERENCES eventos_acceso(id_evento),
    nivel VARCHAR(20),
    origen VARCHAR(50),
    mensaje TEXT,
    tipo VARCHAR(30),
    fecha TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profesores (
    id_profesor SERIAL PRIMARY KEY,
    nombre VARCHAR NOT NULL,
    correo VARCHAR UNIQUE NOT NULL,
    telefono VARCHAR(20) UNIQUE,
    id_cubiculo INTEGER REFERENCES cubiculos(id_cubiculo),
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------------
-- Administrador inicial
-- Email: admin@ipn.mx
-- Contraseña: Admin123!
-- -----------------------------------------------------

INSERT INTO administradores (nombre, apellidos, email, telefono, contrasena, activo, intentos_fallidos)
VALUES (
    'Admin',
    'Principal',
    'admin@ipn.mx',
    '+521234567890',
    '$2b$12$I9a.XUiOYFs01rzl.jGTzutBDgTgBujUENpWO/0ojDrvIxYWr4BS.',
    true,
    0
);