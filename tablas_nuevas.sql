CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table: admins
CREATE TABLE IF NOT EXISTS admins (
    id_admin UUID DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_admin)
);

-- Table: passwords_resets
CREATE TABLE IF NOT EXISTS passwords_resets (
    id_reset UUID DEFAULT gen_random_uuid(),
    id_admin UUID NOT NULL,
    reset_token VARCHAR(255) NOT NULL UNIQUE,
    requested_at VARCHAR(255) NOT NULL, -- Assuming STRING means VARCHAR here, adjust if it's a specific date/time format
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    PRIMARY KEY (id_reset)
    -- FK to admins will be added later
);

-- Table: person_info
CREATE TABLE IF NOT EXISTS person_info (
    id_person UUID DEFAULT gen_random_uuid(),
    first_name VARCHAR(255) NULL,
    first_surname VARCHAR(255) NULL,
    PRIMARY KEY (id_person)
);

-- Table: sexes
CREATE TABLE IF NOT EXISTS sexes (
    id_sex UUID DEFAULT gen_random_uuid(),
    sex VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_sex)
);

-- Table: marital_statuses
CREATE TABLE IF NOT EXISTS marital_statuses (
    id_marital UUID DEFAULT gen_random_uuid(),
    status VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_marital)
);

-- Table: education_levels
CREATE TABLE IF NOT EXISTS education_levels (
    id_education UUID DEFAULT gen_random_uuid(),
    level VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_education)
);

-- Table: (Assuming a table for occupations based on id_occupation FK, naming it 'occupations')
CREATE TABLE IF NOT EXISTS occupations (
    id_occupation UUID DEFAULT gen_random_uuid(),
    occupation_name VARCHAR(255) NOT NULL, -- Example field, adjust as needed
    PRIMARY KEY (id_occupation)
);

-- Table: (Assuming a table for religions based on id_religion FK, naming it 'religions')
CREATE TABLE IF NOT EXISTS religions (
    id_religion UUID DEFAULT gen_random_uuid(),
    religion_name VARCHAR(255) NOT NULL, -- Example field, adjust as needed
    PRIMARY KEY (id_religion)
);

-- Table: legal_statuses
CREATE TABLE IF NOT EXISTS legal_statuses (
    id_legal UUID DEFAULT gen_random_uuid(),
    status VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_legal)
);

-- Table: demographic_info
CREATE TABLE IF NOT EXISTS demographic_info (
    id_demography UUID DEFAULT gen_random_uuid(),
    id_main_person UUID NULL,
    id_sex UUID NULL,
    id_marital UUID NULL,
    id_education UUID NULL,
    id_occupation UUID NULL,
    id_religion UUID NULL,
    id_legal UUID NULL,
    PRIMARY KEY (id_demography)
    -- FKs will be added later
);

-- Table: family_link
CREATE TABLE IF NOT EXISTS family_link (
    id_demography UUID NOT NULL,
    id_person UUID NOT NULL,
    PRIMARY KEY (id_demography, id_person)
    -- FKs will be added later
);

-- Table: countries
CREATE TABLE IF NOT EXISTS countries (
    id_country UUID DEFAULT gen_random_uuid(),
    country VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_country)
);

-- Table: travel_methods
CREATE TABLE IF NOT EXISTS travel_methods (
    id_travel_method UUID DEFAULT gen_random_uuid(),
    method VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_travel_method)
);

-- Table: travel_info
CREATE TABLE IF NOT EXISTS travel_info (
    id_travel UUID DEFAULT gen_random_uuid(),
    departure_date DATE NULL,
    departure_country UUID NULL, -- This will be FK to countries.id_country
    motive_migration TEXT NULL,      -- Using TEXT for potentially longer string
    id_travel_method UUID NULL,
    travel_duration VARCHAR(255) NULL, -- Kept as VARCHAR as DATE might not be appropriate for duration unless specifically formatted
    return_plans TEXT NULL,          -- Using TEXT
    PRIMARY KEY (id_travel)
    -- FKs will be added later
);

-- Table: text_files
CREATE TABLE IF NOT EXISTS text_files (
    id_text UUID DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,             -- Using TEXT for file paths
    story_title VARCHAR(255) NOT NULL,
    story_summary TEXT NOT NULL,    -- Using TEXT
    id_demography UUID NULL,
    id_travel UUID NULL,
    PRIMARY KEY (id_text)
    -- FKs will be added later
);

-- Table: keywords
CREATE TABLE IF NOT EXISTS keywords (
    id_keyword UUID DEFAULT gen_random_uuid(),
    keyword VARCHAR(255) NOT NULL,
    id_text UUID NOT NULL,
    PRIMARY KEY (id_keyword)
    -- FK to text_files will be added later
);

-- Table: image_files
CREATE TABLE IF NOT EXISTS image_files (
    id_img UUID DEFAULT gen_random_uuid(),
    path TEXT NOT NULL,             -- Using TEXT
    title VARCHAR(255) NULL,
    PRIMARY KEY (id_img)
);

-- Table: text_image_link
CREATE TABLE IF NOT EXISTS text_image_link (
    id_text UUID NOT NULL,
    id_img UUID NOT NULL,
    PRIMARY KEY (id_text, id_img)
    -- FKs will be added later
);


-- --- FOREIGN KEY CONSTRAINTS ---
-- (It's generally better to add FKs after all tables are created to avoid order dependencies)

ALTER TABLE passwords_resets
    ADD CONSTRAINT fk_passwords_resets_admin
    FOREIGN KEY (id_admin)
    REFERENCES admins (id_admin);

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_main_person
    FOREIGN KEY (id_main_person)
    REFERENCES person_info (id_person);

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_sex
    FOREIGN KEY (id_sex)
    REFERENCES sexes (id_sex);

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_marital
    FOREIGN KEY (id_marital)
    REFERENCES marital_statuses (id_marital);

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_education
    FOREIGN KEY (id_education)
    REFERENCES education_levels (id_education);

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_occupation
    FOREIGN KEY (id_occupation)
    REFERENCES occupations (id_occupation); -- Assuming 'occupations' table

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_religion
    FOREIGN KEY (id_religion)
    REFERENCES religions (id_religion); -- Assuming 'religions' table

ALTER TABLE demographic_info
    ADD CONSTRAINT fk_demographic_info_legal
    FOREIGN KEY (id_legal)
    REFERENCES legal_statuses (id_legal);

ALTER TABLE family_link
    ADD CONSTRAINT fk_family_link_demography
    FOREIGN KEY (id_demography)
    REFERENCES demographic_info (id_demography);

ALTER TABLE family_link
    ADD CONSTRAINT fk_family_link_person
    FOREIGN KEY (id_person)
    REFERENCES person_info (id_person);

ALTER TABLE travel_info
    ADD CONSTRAINT fk_travel_info_departure_country
    FOREIGN KEY (departure_country)
    REFERENCES countries (id_country);

ALTER TABLE travel_info
    ADD CONSTRAINT fk_travel_info_travel_method
    FOREIGN KEY (id_travel_method)
    REFERENCES travel_methods (id_travel_method);

ALTER TABLE text_files
    ADD CONSTRAINT fk_text_files_demography
    FOREIGN KEY (id_demography)
    REFERENCES demographic_info (id_demography);

ALTER TABLE text_files
    ADD CONSTRAINT fk_text_files_travel
    FOREIGN KEY (id_travel)
    REFERENCES travel_info (id_travel);

ALTER TABLE keywords
    ADD CONSTRAINT fk_keywords_text
    FOREIGN KEY (id_text)
    REFERENCES text_files (id_text);

ALTER TABLE text_image_link
    ADD CONSTRAINT fk_text_image_link_text
    FOREIGN KEY (id_text)
    REFERENCES text_files (id_text);

ALTER TABLE text_image_link
    ADD CONSTRAINT fk_text_image_link_img
    FOREIGN KEY (id_img)
    REFERENCES image_files (id_img);

INSERT INTO sexes (sex) VALUES ('male');
INSERT INTO sexes (sex) VALUES ('female');
