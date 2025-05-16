-- Schema for PostgreSQL
-- Personas
CREATE TABLE IF NOT EXISTS personas (
    persona_id        SERIAL       PRIMARY KEY,
    nombre            VARCHAR(100) NOT NULL,
    apellido          VARCHAR(100) NOT NULL,
    fecha_nacimiento  DATE,
    pais_origen       VARCHAR(100),
    genero            VARCHAR(20),
    fecha_registro    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    email             VARCHAR(100),
    telefono          VARCHAR(20)
);

-- Relatos de Emigración
CREATE TABLE IF NOT EXISTS relatos_emigracion (
    relato_id     SERIAL    PRIMARY KEY,
    persona_id    BIGINT    NOT NULL REFERENCES personas(persona_id) ON DELETE CASCADE,
    texto_relato  TEXT      NOT NULL,
    fecha_relato  DATE      NOT NULL,
    titulo_relato VARCHAR(200)
);

-- Palabras Clave
CREATE TABLE IF NOT EXISTS palabras_clave (
    palabra_clave_id SERIAL      PRIMARY KEY,
    palabra          VARCHAR(100) NOT NULL UNIQUE,
    descripcion      TEXT
);

-- Relatos ↔ Palabras Clave
CREATE TABLE IF NOT EXISTS relatos_palabras (
    relato_palabra_id SERIAL      PRIMARY KEY,
    relato_id         BIGINT      NOT NULL REFERENCES relatos_emigracion(relato_id) ON DELETE CASCADE,
    palabra_clave_id  BIGINT      NOT NULL REFERENCES palabras_clave(palabra_clave_id) ON DELETE CASCADE,
    frecuencia        INTEGER     NOT NULL,
    fecha_analisis    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- Tendencias de Palabras Clave
CREATE TABLE IF NOT EXISTS tendencias_palabras (
    tendencia_id        SERIAL     PRIMARY KEY,
    palabra_clave_id    BIGINT     NOT NULL REFERENCES palabras_clave(palabra_clave_id) ON DELETE CASCADE,
    periodo             VARCHAR(100) NOT NULL,
    tendencia           REAL       CHECK (tendencia >= -1 AND tendencia <= 1),
    descripcion_tendencia TEXT
);

-- Gráficos de Tendencias
CREATE TABLE IF NOT EXISTS graficos_tendencias (
    grafico_tendencia_id SERIAL     PRIMARY KEY,
    tendencia_id         BIGINT     NOT NULL REFERENCES tendencias_palabras(tendencia_id) ON DELETE CASCADE,
    tipo_grafico         VARCHAR(100) NOT NULL,
    datos_grafico        JSONB
);

-- Usuarios Administrador
CREATE TABLE IF NOT EXISTS usuarios_administrador (
    admin_id            SERIAL     PRIMARY KEY,
    correo              VARCHAR(100) NOT NULL UNIQUE,
    contrasena          VARCHAR(255) NOT NULL,
    ultima_fecha_cambio TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_relatos_persona         ON relatos_emigracion(persona_id);
CREATE INDEX IF NOT EXISTS idx_relatos_palabras_relato ON relatos_palabras(relato_id);
CREATE INDEX IF NOT EXISTS idx_relatos_palabras_palabra ON relatos_palabras(palabra_clave_id);
CREATE INDEX IF NOT EXISTS idx_tendencias_palabra       ON tendencias_palabras(palabra_clave_id);
CREATE INDEX IF NOT EXISTS idx_graficos_tendencia       ON graficos_tendencias(tendencia_id);