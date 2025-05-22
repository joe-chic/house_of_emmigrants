-- Enable pgcrypto extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table: sexes
CREATE TABLE sexes (
    id_sex UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sex TEXT NOT NULL UNIQUE
);

-- Table: travel_methods
CREATE TABLE travel_methods (
    id_travel_method UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    method TEXT NOT NULL UNIQUE
);

-- Table: marital_statuses
CREATE TABLE marital_statuses (
    id_marital UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL UNIQUE
);

-- Table: education_levels
CREATE TABLE education_levels (
    id_education UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level TEXT NOT NULL UNIQUE
);

-- Table: legal_statuses
CREATE TABLE legal_statuses (
    id_legal UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL UNIQUE
);

-- Table: motives_migration
CREATE TABLE motives_migration (
    id_motive UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    motive TEXT NOT NULL UNIQUE
);

-- Table: admins
CREATE TABLE admins (
    id_admin UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- Table: person_info
CREATE TABLE person_info (
    id_person UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NULL,
    first_surname TEXT NULL
);

-- Table: countries
CREATE TABLE countries (
    id_country UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL UNIQUE -- Added UNIQUE constraint as country names should be unique
);

-- Table: cities
CREATE TABLE cities (
    id_city UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_country UUID NULL, -- This will be a FK to countries.id_country
    city TEXT NOT NULL
    -- Consider adding UNIQUE constraint on (city, id_country) if city names are unique per country
);

-- Table: demographic_info
CREATE TABLE demographic_info (
    id_demography UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_main_person UUID NULL,
    id_sex UUID NULL,
    id_marital UUID NULL,
    id_education UUID NULL,
    id_occupation UUID NULL, -- Assuming this will link to an occupations table with UUID PK
    id_religion UUID NULL,   -- Assuming this will link to a religions table with UUID PK
    id_legal UUID NULL
);

-- Table: travel_info
CREATE TABLE travel_info (
    id_travel UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    departure_date DATE NULL,
    destination_city UUID NULL, -- This will be a FK to cities.id_city
    id_motive_migration UUID NULL,
    travel_duration TEXT NULL, -- Changed from DATE to TEXT as duration can be 'X years, Y months' etc. or a period.
                               -- If it's a specific end date, DATE might be fine.
                               -- If it's a duration, INTERVAL might be better. TEXT is flexible.
    return_plans TEXT NULL
);

-- Table: image_files
CREATE TABLE image_files (
    id_img UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    title TEXT NULL
);

-- Table: text_files
CREATE TABLE text_files (
    id_text UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,
    story_title TEXT NOT NULL,
    story_summary TEXT NOT NULL,
    id_demography UUID NOT NULL,
    id_travel UUID NULL
);

-- Table: keywords
CREATE TABLE keywords (
    id_keyword UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    id_text UUID NOT NULL
);

-- Table: mention_link (Junction table for many-to-many between demographic_info and person_info)
CREATE TABLE mention_link (
    id_demography UUID NOT NULL,
    id_person UUID NOT NULL,
    PRIMARY KEY (id_demography, id_person)
);

-- Table: text_image_link (Junction table for many-to-many between text_files and image_files)
CREATE TABLE text_image_link (
    id_text UUID NOT NULL,
    id_img UUID NOT NULL,
    PRIMARY KEY (id_text, id_img)
);

-- Table: passwords_resets
CREATE TABLE passwords_resets (
    id_reset UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_admin UUID NOT NULL,
    reset_token TEXT NOT NULL UNIQUE,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Changed to TIMESTAMP WITH TIME ZONE
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE NULL
);

-- Table: travel_link (Junction table for many-to-many between travel_info and travel_methods)
CREATE TABLE travel_link (
    id_travel UUID NOT NULL,
    id_travel_method UUID NOT NULL,
    PRIMARY KEY (id_travel, id_travel_method)
);


-- Foreign Key Constraints

ALTER TABLE demographic_info
ADD CONSTRAINT fk_demographic_info_id_main_person FOREIGN KEY (id_main_person) REFERENCES person_info(id_person) ON DELETE SET NULL,
ADD CONSTRAINT fk_demographic_info_id_sex FOREIGN KEY (id_sex) REFERENCES sexes(id_sex) ON DELETE SET NULL,
ADD CONSTRAINT fk_demographic_info_id_marital FOREIGN KEY (id_marital) REFERENCES marital_statuses(id_marital) ON DELETE SET NULL,
ADD CONSTRAINT fk_demographic_info_id_education FOREIGN KEY (id_education) REFERENCES education_levels(id_education) ON DELETE SET NULL,
ADD CONSTRAINT fk_demographic_info_id_legal FOREIGN KEY (id_legal) REFERENCES legal_statuses(id_legal) ON DELETE SET NULL;
-- Note: FKs for id_occupation and id_religion would be added if/when those tables are created.

ALTER TABLE cities
ADD CONSTRAINT fk_cities_id_country FOREIGN KEY (id_country) REFERENCES countries(id_country) ON DELETE SET NULL;

ALTER TABLE travel_info
ADD CONSTRAINT fk_travel_info_destination_city FOREIGN KEY (destination_city) REFERENCES cities(id_city) ON DELETE SET NULL,
ADD CONSTRAINT fk_travel_info_id_motive_migration FOREIGN KEY (id_motive_migration) REFERENCES motives_migration(id_motive) ON DELETE SET NULL;

ALTER TABLE text_files
ADD CONSTRAINT fk_text_files_id_demography FOREIGN KEY (id_demography) REFERENCES demographic_info(id_demography) ON DELETE CASCADE, -- Cascade if a demographic record is core to a text file
ADD CONSTRAINT fk_text_files_id_travel FOREIGN KEY (id_travel) REFERENCES travel_info(id_travel) ON DELETE SET NULL;

ALTER TABLE keywords
ADD CONSTRAINT fk_keywords_id_text FOREIGN KEY (id_text) REFERENCES text_files(id_text) ON DELETE CASCADE;

ALTER TABLE mention_link
ADD CONSTRAINT fk_mention_link_id_demography FOREIGN KEY (id_demography) REFERENCES demographic_info(id_demography) ON DELETE CASCADE,
ADD CONSTRAINT fk_mention_link_id_person FOREIGN KEY (id_person) REFERENCES person_info(id_person) ON DELETE CASCADE;

ALTER TABLE text_image_link
ADD CONSTRAINT fk_text_image_link_id_text FOREIGN KEY (id_text) REFERENCES text_files(id_text) ON DELETE CASCADE,
ADD CONSTRAINT fk_text_image_link_id_img FOREIGN KEY (id_img) REFERENCES image_files(id_img) ON DELETE CASCADE;

ALTER TABLE passwords_resets
ADD CONSTRAINT fk_passwords_resets_id_admin FOREIGN KEY (id_admin) REFERENCES admins(id_admin) ON DELETE CASCADE;

ALTER TABLE travel_link
ADD CONSTRAINT fk_travel_link_id_travel FOREIGN KEY (id_travel) REFERENCES travel_info(id_travel) ON DELETE CASCADE,
ADD CONSTRAINT fk_travel_link_id_travel_method FOREIGN KEY (id_travel_method) REFERENCES travel_methods(id_travel_method) ON DELETE CASCADE;


-- Data Inserts for Lookup Tables (IDs will be auto-generated UUIDs)

-- Inserts for sexes
INSERT INTO sexes (sex) VALUES ('female');
INSERT INTO sexes (sex) VALUES ('male');

-- Inserts for travel_methods
INSERT INTO travel_methods (method) VALUES ('steamship');
INSERT INTO travel_methods (method) VALUES ('sailboat');
INSERT INTO travel_methods (method) VALUES ('train');
INSERT INTO travel_methods (method) VALUES ('horse-drawn carriage');
INSERT INTO travel_methods (method) VALUES ('on foot');
INSERT INTO travel_methods (method) VALUES ('wagon or cart');
INSERT INTO travel_methods (method) VALUES ('automobile');

-- Inserts for marital_statuses
INSERT INTO marital_statuses (status) VALUES ('single');
INSERT INTO marital_statuses (status) VALUES ('married');
INSERT INTO marital_statuses (status) VALUES ('widowed');
INSERT INTO marital_statuses (status) VALUES ('divorced');
INSERT INTO marital_statuses (status) VALUES ('separated');
INSERT INTO marital_statuses (status) VALUES ('engaged');

-- Inserts for education_levels
INSERT INTO education_levels (level) VALUES ('no formal education');
INSERT INTO education_levels (level) VALUES ('primary school');
INSERT INTO education_levels (level) VALUES ('some secondary school');
INSERT INTO education_levels (level) VALUES ('completed secondary school');
INSERT INTO education_levels (level) VALUES ('trade or vocational training');
INSERT INTO education_levels (level) VALUES ('some college/university');
INSERT INTO education_levels (level) VALUES ('completed college/university');
INSERT INTO education_levels (level) VALUES ('illiterate');

-- Inserts for legal_statuses
INSERT INTO legal_statuses (status) VALUES ('citizen of origin country');
INSERT INTO legal_statuses (status) VALUES ('stateless');
INSERT INTO legal_statuses (status) VALUES ('refugee');
INSERT INTO legal_statuses (status) VALUES ('asylum seeker');
INSERT INTO legal_statuses (status) VALUES ('undocumented');
INSERT INTO legal_statuses (status) VALUES ('naturalized citizen');
INSERT INTO legal_statuses (status) VALUES ('legal immigrant');
INSERT INTO legal_statuses (status) VALUES ('temporary resident');

-- Inserts for motives_migration
INSERT INTO motives_migration (motive) VALUES ('economic opportunity');
INSERT INTO motives_migration (motive) VALUES ('family reunification');
INSERT INTO motives_migration (motive) VALUES ('religious persecution');
INSERT INTO motives_migration (motive) VALUES ('political persecution');
INSERT INTO motives_migration (motive) VALUES ('war/conflict');
INSERT INTO motives_migration (motive) VALUES ('famine or natural disaster');
INSERT INTO motives_migration (motive) VALUES ('education');
INSERT INTO motives_migration (motive) VALUES ('adventure');
INSERT INTO motives_migration (motive) VALUES ('land ownership');
INSERT INTO motives_migration (motive) VALUES ('forced migration');


-- create a test admin with email/password you choose
INSERT INTO admins (id_admin, email, password)
VALUES (
  gen_random_uuid(),
  'admin@example.com',
  '666'
);

-- verify it’s there
SELECT id_admin, email, password
FROM admins
WHERE email = 'admin@example.com';

-- 1) Detalles completos de historias migratorias
CREATE OR REPLACE FUNCTION get_story_details()
RETURNS TABLE (
  story_title           TEXT,
  story_summary         TEXT,
  main_first            TEXT,
  main_last             TEXT,
  sex                   TEXT,
  marital_status        TEXT,
  education_level       TEXT,
  legal_status          TEXT,
  mentions              TEXT[],
  departure_date        DATE,
  destination_city      TEXT,
  destination_country   TEXT,
  motive                TEXT,
  travel_duration       TEXT,
  return_plans          TEXT,
  methods               TEXT[]
)
LANGUAGE sql AS
$$
  SELECT
    tf.story_title,
    tf.story_summary,
    pi_main.first_name   AS main_first,
    pi_main.first_surname AS main_last,
    s.sex,
    ms.status           AS marital_status,
    el.level            AS education_level,
    ls.status           AS legal_status,
    ARRAY_AGG(pi_ment.first_name || ' ' || pi_ment.first_surname)
      FILTER (WHERE pi_ment.id_person IS NOT NULL) AS mentions,
    ti.departure_date,
    c.city              AS destination_city,
    co.country          AS destination_country,
    mm.motive,
    ti.travel_duration,
    ti.return_plans,
    ARRAY_AGG(tm.method) AS methods
  FROM text_files tf
  LEFT JOIN demographic_info di ON tf.id_demography = di.id_demography
  LEFT JOIN person_info pi_main ON di.id_main_person = pi_main.id_person
  LEFT JOIN sexes s ON di.id_sex = s.id_sex
  LEFT JOIN marital_statuses ms ON di.id_marital = ms.id_marital
  LEFT JOIN education_levels el ON di.id_education = el.id_education
  LEFT JOIN legal_statuses ls ON di.id_legal = ls.id_legal
  LEFT JOIN mention_link ml ON tf.id_demography = ml.id_demography
  LEFT JOIN person_info pi_ment ON ml.id_person = pi_ment.id_person
  LEFT JOIN travel_info ti ON tf.id_travel = ti.id_travel
  LEFT JOIN cities c ON ti.destination_city = c.id_city
  LEFT JOIN countries co ON c.id_country = co.id_country
  LEFT JOIN motives_migration mm ON ti.id_motive_migration = mm.id_motive
  LEFT JOIN travel_link tl ON ti.id_travel = tl.id_travel
  LEFT JOIN travel_methods tm ON tl.id_travel_method = tm.id_travel_method
  GROUP BY
    tf.story_title, tf.story_summary,
    pi_main.id_person, s.sex, ms.status, el.level, ls.status,
    ti.departure_date, c.city, co.country, mm.motive,
    ti.travel_duration, ti.return_plans
  ORDER BY ti.departure_date DESC;
$$;

-- 2) Distribución por ciudad de destino
CREATE OR REPLACE FUNCTION get_city_distribution()
RETURNS TABLE (
  city TEXT,
  cnt  BIGINT
)
LANGUAGE sql AS
$$
  SELECT
    c.city,
    COUNT(*) AS cnt
  FROM travel_info ti
  JOIN cities c ON ti.destination_city = c.id_city
  GROUP BY c.city
  ORDER BY cnt DESC;
$$;

-- 3) Top N palabras clave más frecuentes (default 10)
CREATE OR REPLACE FUNCTION get_top_keywords(p_limit INT DEFAULT 10)
RETURNS TABLE (
  keyword TEXT,
  freq    BIGINT
)
LANGUAGE sql AS
$$
  SELECT
    keyword,
    COUNT(*) AS freq
  FROM keywords
  GROUP BY keyword
  ORDER BY freq DESC
  LIMIT p_limit;
$$;

-- 4) Viajes por mes para cada año
CREATE OR REPLACE FUNCTION get_monthly_travels()
RETURNS TABLE (
  year        INT,
  month       TEXT,
  month_order INT,
  total       BIGINT
)
LANGUAGE sql AS
$$
  SELECT
    EXTRACT(YEAR FROM departure_date)::INT AS year,
    TO_CHAR(departure_date, 'Mon')       AS month,
    EXTRACT(MONTH FROM departure_date)::INT AS month_order,
    COUNT(*)                             AS total
  FROM travel_info
  WHERE departure_date IS NOT NULL
  GROUP BY year, month, month_order
  ORDER BY year, month_order;
$$;

-- 5) Viajes por año
CREATE OR REPLACE FUNCTION get_yearly_travels()
RETURNS TABLE (
  year  INT,
  total BIGINT
)
LANGUAGE sql AS
$$
  SELECT
    EXTRACT(YEAR FROM departure_date)::INT AS year,
    COUNT(*)                             AS total
  FROM travel_info
  WHERE departure_date IS NOT NULL
  GROUP BY year
  ORDER BY year;
$$;