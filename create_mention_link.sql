-- Crear tabla mention_link que falta en la base de datos actual
CREATE TABLE mention_link (
    id_demography INTEGER NOT NULL,
    id_person INTEGER NOT NULL,
    PRIMARY KEY (id_demography, id_person),
    CONSTRAINT fk_mention_link_id_demography FOREIGN KEY (id_demography) REFERENCES demographic_info(id_demography) ON DELETE CASCADE,
    CONSTRAINT fk_mention_link_id_person FOREIGN KEY (id_person) REFERENCES person_info(id_person) ON DELETE CASCADE
);

-- Confirmar creación
SELECT 'Tabla mention_link creada exitosamente.' as resultado; 