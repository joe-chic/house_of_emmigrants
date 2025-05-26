-- Get ID from 'sexes'
CREATE OR REPLACE FUNCTION get_sex_id_by_name(p_sex_name TEXT)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_sex_name IS NULL OR p_sex_name = '' THEN RETURN NULL; END IF;
    SELECT id_sex INTO v_id FROM sexes WHERE lower(sex) = lower(trim(p_sex_name));
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'marital_statuses'
CREATE OR REPLACE FUNCTION get_marital_status_id_by_name(p_status_name TEXT)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_status_name IS NULL OR p_status_name = '' THEN RETURN NULL; END IF;
    SELECT id_marital INTO v_id FROM marital_statuses WHERE lower(status) = lower(trim(p_status_name));
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'legal_statuses'
CREATE OR REPLACE FUNCTION get_legal_status_id_by_name(p_status_name TEXT)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_status_name IS NULL OR p_status_name = '' THEN RETURN NULL; END IF;
    SELECT id_legal INTO v_id FROM legal_statuses WHERE lower(status) = lower(trim(p_status_name));
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'countries'
CREATE OR REPLACE FUNCTION get_country_id_by_name(p_country_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_country_name IS NULL OR p_country_name = '' THEN RETURN NULL; END IF;
    SELECT id_country INTO v_id FROM countries WHERE lower(country) = lower(trim(p_country_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO countries (country) VALUES (trim(p_country_name)) RETURNING id_country INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'cities' (or create if needed, linking to country)
CREATE OR REPLACE FUNCTION get_city_id_by_name(p_city_name TEXT, p_country_id INT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_city_name IS NULL OR p_city_name = '' THEN RETURN NULL; END IF;
    SELECT id_city INTO v_id FROM cities 
    WHERE lower(city) = lower(trim(p_city_name)) AND (cities.id_country = p_country_id OR (cities.id_country IS NULL AND p_country_id IS NULL));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO cities (city, id_country) VALUES (trim(p_city_name), p_country_id) RETURNING id_city INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'travel_types'
CREATE OR REPLACE FUNCTION get_travel_type_id_by_name(p_type_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_type_name IS NULL OR p_type_name = '' THEN RETURN NULL; END IF;
    SELECT id_type INTO v_id FROM travel_types WHERE lower(type) = lower(trim(p_type_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO travel_types (type) VALUES (trim(p_type_name)) RETURNING id_type INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'education_levels'
CREATE OR REPLACE FUNCTION get_education_level_id_by_name(p_level_name TEXT)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_level_name IS NULL OR p_level_name = '' THEN RETURN NULL; END IF;
    SELECT id_education INTO v_id FROM education_levels WHERE lower(level) = lower(trim(p_level_name));
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'relationships'
CREATE OR REPLACE FUNCTION get_relationship_id_by_name(p_rel_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_rel_name IS NULL OR p_rel_name = '' THEN RETURN NULL; END IF;
    SELECT id_relationship INTO v_id FROM relationships WHERE lower(relationship_type) = lower(trim(p_rel_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO relationships (relationship_type) VALUES (trim(p_rel_name)) RETURNING id_relationship INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'cultures'
CREATE OR REPLACE FUNCTION get_culture_id_by_name(p_culture_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_culture_name IS NULL OR p_culture_name = '' THEN RETURN NULL; END IF;
    SELECT id_culture INTO v_id FROM cultures WHERE lower(name) = lower(trim(p_culture_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO cultures (name) VALUES (trim(p_culture_name)) RETURNING id_culture INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'languages'
CREATE OR REPLACE FUNCTION get_language_id_by_name(p_lang_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_lang_name IS NULL OR p_lang_name = '' THEN RETURN NULL; END IF;
    SELECT id_language INTO v_id FROM languages WHERE lower(name) = lower(trim(p_lang_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO languages (name) VALUES (trim(p_lang_name)) RETURNING id_language INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'historic_events'
CREATE OR REPLACE FUNCTION get_historic_event_id_by_name(p_event_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_event_name IS NULL OR p_event_name = '' THEN RETURN NULL; END IF;
    SELECT id_event INTO v_id FROM historic_events WHERE lower(historic_event) = lower(trim(p_event_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO historic_events (historic_event) VALUES (trim(p_event_name)) RETURNING id_event INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Get ID from 'schools'
CREATE OR REPLACE FUNCTION get_school_id_by_name(p_school_name TEXT, p_create_if_not_exists BOOLEAN DEFAULT FALSE)
RETURNS INT AS $$
DECLARE v_id INT;
BEGIN
    IF p_school_name IS NULL OR p_school_name = '' THEN RETURN NULL; END IF;
    SELECT id_school INTO v_id FROM schools WHERE lower(name) = lower(trim(p_school_name));
    IF v_id IS NULL AND p_create_if_not_exists THEN
        INSERT INTO schools (name) VALUES (trim(p_school_name)) RETURNING id_school INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper to find or create a person (people table)
-- Now returns the ID of the found or created person
CREATE OR REPLACE FUNCTION find_or_create_person(
    p_full_name TEXT,
    p_birthday TEXT DEFAULT NULL, -- YYYY-MM-DD string
    p_birthplace_city_name TEXT DEFAULT NULL,
    p_birthplace_country_name TEXT DEFAULT NULL,
    p_sex_name TEXT DEFAULT NULL,
    p_marital_status_name TEXT DEFAULT NULL,
    p_legal_status_name TEXT DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    v_person_id INT;
    v_parsed_birthday DATE;
    v_birth_city_id INT;
    v_birth_country_id INT;
    v_sex_id INT;
    v_marital_id INT;
    v_legal_id INT;
    v_name_trimmed TEXT := trim(p_full_name);
BEGIN
    IF v_name_trimmed IS NULL OR v_name_trimmed = '' THEN
        RAISE NOTICE 'Cannot find or create person with empty name.';
        RETURN NULL;
    END IF;

    -- Attempt to find an existing person by full name (simplistic match)
    SELECT id_people INTO v_person_id FROM people WHERE lower(name) = lower(v_name_trimmed) LIMIT 1;

    IF v_person_id IS NULL THEN
        -- Parse birthday
        BEGIN v_parsed_birthday := p_birthday::DATE; EXCEPTION WHEN OTHERS THEN v_parsed_birthday := NULL; END;
        
        -- Get FK IDs
        v_birth_country_id := get_country_id_by_name(p_birthplace_country_name, TRUE);
        IF v_birth_country_id IS NOT NULL THEN
            v_birth_city_id := get_city_id_by_name(p_birthplace_city_name, v_birth_country_id, TRUE);
        ELSE
            v_birth_city_id := get_city_id_by_name(p_birthplace_city_name, NULL, TRUE); -- City without country if country unknown
        END IF;
        
        v_sex_id := get_sex_id_by_name(p_sex_name);
        v_marital_id := get_marital_status_id_by_name(p_marital_status_name);
        v_legal_id := get_legal_status_id_by_name(p_legal_status_name);

        INSERT INTO people (name, birthday, birthplace_city, birthplace_country, sex, marital_status, legal_status)
        VALUES (v_name_trimmed, v_parsed_birthday, v_birth_city_id, v_birth_country_id, v_sex_id, v_marital_id, v_legal_id)
        RETURNING id_people INTO v_person_id;
    END IF;
    RETURN v_person_id;
END;
$$ LANGUAGE plpgsql;
