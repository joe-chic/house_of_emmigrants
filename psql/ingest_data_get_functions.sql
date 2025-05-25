-- Helper to get id_sex from sexes table
CREATE OR REPLACE FUNCTION get_sex_id(p_sex_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_sex INTO v_id FROM sexes WHERE lower(sex) = lower(p_sex_name);
    RETURN v_id; -- Returns NULL if not found
END;
$$ LANGUAGE plpgsql;

-- Helper to get id_marital from marital_statuses table
CREATE OR REPLACE FUNCTION get_marital_status_id(p_status_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_marital INTO v_id FROM marital_statuses WHERE lower(status) = lower(p_status_name);
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper for education_level
CREATE OR REPLACE FUNCTION get_education_level_id(p_level_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_education INTO v_id FROM education_levels WHERE lower(level) = lower(p_level_name);
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper for legal_status
CREATE OR REPLACE FUNCTION get_legal_status_id(p_status_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_legal INTO v_id FROM legal_statuses WHERE lower(status) = lower(p_status_name);
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper for motive_migration
CREATE OR REPLACE FUNCTION get_motive_migration_id(p_motive_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_motive INTO v_id FROM motives_migration WHERE lower(motive) = lower(p_motive_name);
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper for travel_method
CREATE OR REPLACE FUNCTION get_travel_method_id(p_method_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    SELECT id_travel_method INTO v_id FROM travel_methods WHERE lower(method) = lower(p_method_name);
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper for country
CREATE OR REPLACE FUNCTION get_country_id(p_country_name TEXT)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    -- Consider more robust matching (e.g., case-insensitive, trimming whitespace)
    SELECT id_country INTO v_id FROM countries WHERE lower(country) = lower(p_country_name);
    IF v_id IS NULL AND p_country_name IS NOT NULL AND p_country_name <> '' THEN
        -- Optionally, insert the new country if it doesn't exist
        -- For now, we'll just return NULL if not found to be strict.
        -- INSERT INTO countries (country) VALUES (p_country_name) RETURNING id_country INTO v_id;
    END IF;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Helper to find/create a city and return its ID (simplified)
-- This is tricky: if AI only gives country, what city do we use?
-- This function will try to find ANY city for the country, or create a placeholder city.
CREATE OR REPLACE FUNCTION get_or_create_city_for_country(
    p_country_name TEXT, 
    p_city_name_placeholder TEXT DEFAULT 'Unknown City' -- Placeholder if no specific city known for the country
)
RETURNS UUID AS $$
DECLARE
    v_country_id UUID;
    v_city_id UUID;
BEGIN
    v_country_id := get_country_id(p_country_name);
    IF v_country_id IS NULL THEN
        RETURN NULL; -- No country, no city
    END IF;

    -- Try to find an existing city for this country (e.g., a capital or a placeholder)
    -- This logic needs to be adapted based on how you want to handle city mapping.
    -- For simplicity, let's assume we look for a city named after the country or a generic placeholder.
    SELECT id_city INTO v_city_id FROM cities 
    WHERE id_country = v_country_id AND lower(city) = lower(p_city_name_placeholder || ' - ' || p_country_name) 
    LIMIT 1;

    IF v_city_id IS NULL THEN
        -- Create a placeholder city for this country if one doesn't exist
        INSERT INTO cities (city, id_country) 
        VALUES (p_city_name_placeholder || ' - ' || p_country_name, v_country_id) 
        RETURNING id_city INTO v_city_id;
    END IF;
    RETURN v_city_id;
END;
$$ LANGUAGE plpgsql;

-- Helper to find or create a person and return their ID
CREATE OR REPLACE FUNCTION get_or_create_person_id(
    p_first_name TEXT,
    p_last_name TEXT
)
RETURNS UUID AS $$
DECLARE
    v_person_id UUID;
    v_first_name_trimmed TEXT := trim(p_first_name);
    v_last_name_trimmed TEXT := trim(p_last_name);
BEGIN
    IF v_first_name_trimmed = '' AND v_last_name_trimmed = '' THEN
        RETURN NULL; -- Not enough info to create a person
    END IF;

    -- Try to find existing person (simple match by name - might need more robust logic)
    SELECT id_person INTO v_person_id FROM person_info 
    WHERE lower(first_name) = lower(v_first_name_trimmed) 
      AND (lower(first_surname) = lower(v_last_name_trimmed) OR (first_surname IS NULL AND v_last_name_trimmed = ''));
      -- Added OR condition for cases where last name might be null or empty string.

    IF v_person_id IS NULL THEN
        INSERT INTO person_info (first_name, first_surname) 
        VALUES (v_first_name_trimmed, CASE WHEN v_last_name_trimmed = '' THEN NULL ELSE v_last_name_trimmed END) 
        RETURNING id_person INTO v_person_id;
    END IF;
    RETURN v_person_id;
END;
$$ LANGUAGE plpgsql;
