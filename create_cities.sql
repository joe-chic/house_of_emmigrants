-- Crear tabla cities que falta en la base de datos actual
CREATE TABLE cities (
    id_city SERIAL PRIMARY KEY,
    id_country INTEGER NULL,
    city VARCHAR(100) NOT NULL,
    CONSTRAINT fk_cities_id_country FOREIGN KEY (id_country) REFERENCES countries(id_country) ON DELETE SET NULL
);

-- Confirmar creación
SELECT 'Tabla cities creada exitosamente.' as resultado; 