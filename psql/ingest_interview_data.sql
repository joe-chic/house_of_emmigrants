CREATE OR REPLACE PROCEDURE ingest_interview_data(
    -- From text_files
    p_text_file_path TEXT, -- You'll need to pass the path of the text file being processed
    p_story_title TEXT,
    p_story_summary TEXT,
    -- Interviewee details
    p_first_name_interviewed TEXT,
    p_first_surname_interviewed TEXT,
    p_sex_interviewed TEXT,
    p_marital_status_interviewed TEXT,
    p_education_level_interviewed TEXT,
    p_occupation_interviewed TEXT, -- Assuming this is a TEXT field for now in demographic_info
    p_religion_interviewed TEXT,   -- Assuming this is a TEXT field for now in demographic_info
    p_legal_status_interviewed TEXT,
    -- Other mentioned people
    p_fullname_others TEXT[], -- Array of "FirstName LastName"
    -- Travel details
    p_departure_date TEXT, -- Needs to be parsed to DATE
    p_destination_country TEXT,
    p_motive_migration TEXT,
    p_travel_methods TEXT[], -- Array of travel method names
    p_return_plans TEXT,
    p_travel_duration TEXT, -- Assuming this is a TEXT field in travel_info
    -- Keywords
    p_important_keywords TEXT[],
    -- OUT parameters for generated IDs (optional, but useful for confirmation)
    OUT p_created_text_id UUID,
    OUT p_created_person_id UUID,
    OUT p_created_demography_id UUID,
    OUT p_created_travel_id UUID
)
LANGUAGE plpgsql AS $$
DECLARE
    v_main_person_id UUID;
    v_sex_id UUID;
    v_marital_id UUID;
    v_education_id UUID;
    v_legal_id UUID;
    v_demography_id UUID;
    v_travel_id UUID;
    v_country_id UUID;
    v_city_id UUID;
    v_motive_id UUID;
    v_text_id UUID;
    v_departure_parsed_date DATE;
    mentioned_person_name TEXT;
    mentioned_person_id UUID;
    travel_method_name TEXT;
    travel_method_id UUID;
    keyword_text TEXT;
    name_parts TEXT[];
    mentioned_first_name TEXT;
    mentioned_last_name TEXT;
BEGIN
    -- Ensure this all runs in a transaction (handled by the calling Python code)

    -- 1. Get/Create main interviewee person_info
    v_main_person_id := get_or_create_person_id(p_first_name_interviewed, p_first_surname_interviewed);
    p_created_person_id := v_main_person_id;

    -- 2. Get IDs from lookup tables for demographic_info
    v_sex_id := get_sex_id(p_sex_interviewed);
    v_marital_id := get_marital_status_id(p_marital_status_interviewed);
    v_education_id := get_education_level_id(p_education_level_interviewed);
    v_legal_id := get_legal_status_id(p_legal_status_interviewed);
    -- Note: p_occupation_interviewed and p_religion_interviewed are inserted as text directly for now.
    -- If you have lookup tables for them, you'd create helper functions like the ones above.

    -- 3. Insert demographic_info
    IF v_main_person_id IS NOT NULL THEN
        INSERT INTO demographic_info (
            id_main_person, id_sex, id_marital, id_education, id_legal
            -- Add occupation and religion text fields if they exist in your demographic_info table
            -- For example: , occupation_text, religion_text 
        ) VALUES (
            v_main_person_id, v_sex_id, v_marital_id, v_education_id, v_legal_id
            -- , p_occupation_interviewed, p_religion_interviewed 
        ) RETURNING id_demography INTO v_demography_id;
        p_created_demography_id := v_demography_id;
    END IF;

    -- 4. Handle mentioned people (fullname_others)
    IF v_demography_id IS NOT NULL AND p_fullname_others IS NOT NULL THEN
        FOREACH mentioned_person_name IN ARRAY p_fullname_others LOOP
            IF mentioned_person_name <> '' THEN
                -- Basic split of "FirstName LastName" - might need more robust parsing
                name_parts := string_to_array(trim(mentioned_person_name), ' ');
                mentioned_first_name := name_parts[1];
                IF array_length(name_parts, 1) > 1 THEN
                    mentioned_last_name := array_to_string(name_parts[2:array_length(name_parts, 1)], ' ');
                ELSE
                    mentioned_last_name := ''; -- Or NULL
                END IF;

                mentioned_person_id := get_or_create_person_id(mentioned_first_name, mentioned_last_name);
                IF mentioned_person_id IS NOT NULL THEN
                    -- Avoid duplicate entries in mention_link
                    INSERT INTO mention_link (id_demography, id_person)
                    VALUES (v_demography_id, mentioned_person_id)
                    ON CONFLICT (id_demography, id_person) DO NOTHING;
                END IF;
            END IF;
        END LOOP;
    END IF;

    -- 5. Handle travel_info
    -- Parse departure date
    BEGIN
        v_departure_parsed_date := p_departure_date::DATE;
    EXCEPTION WHEN OTHERS THEN
        v_departure_parsed_date := NULL; -- Handle invalid date strings
    END;

    v_city_id := get_or_create_city_for_country(p_destination_country);
    v_motive_id := get_motive_migration_id(p_motive_migration);

    INSERT INTO travel_info (
        departure_date, destination_city, id_motive_migration, travel_duration, return_plans
    ) VALUES (
        v_departure_parsed_date, v_city_id, v_motive_id, p_travel_duration, p_return_plans
    ) RETURNING id_travel INTO v_travel_id;
    p_created_travel_id := v_travel_id;

    -- 6. Link travel_methods to travel_info via travel_link
    IF v_travel_id IS NOT NULL AND p_travel_methods IS NOT NULL THEN
        FOREACH travel_method_name IN ARRAY p_travel_methods LOOP
            travel_method_id := get_travel_method_id(travel_method_name);
            IF travel_method_id IS NOT NULL THEN
                -- Avoid duplicate entries
                INSERT INTO travel_link (id_travel, id_travel_method)
                VALUES (v_travel_id, travel_method_id)
                ON CONFLICT (id_travel, id_travel_method) DO NOTHING;
            END IF;
        END LOOP;
    END IF;

    -- 7. Insert text_files record
    IF v_demography_id IS NOT NULL THEN -- Require demography to link text
        INSERT INTO text_files (
            path, story_title, story_summary, id_demography, id_travel
        ) VALUES (
            p_text_file_path, p_story_title, p_story_summary, v_demography_id, v_travel_id
        ) RETURNING id_text INTO v_text_id;
        p_created_text_id := v_text_id;
    END IF;

    -- 8. Insert important_keywords
    IF v_text_id IS NOT NULL AND p_important_keywords IS NOT NULL THEN
        FOREACH keyword_text IN ARRAY p_important_keywords LOOP
            IF keyword_text <> '' THEN
                -- Avoid duplicate keywords for the same text file if desired,
                -- or let duplicates exist if that's the design.
                -- Current keywords table PK is id_keyword (UUID), so duplicates are allowed per text.
                -- If (id_text, keyword) should be unique, add a unique constraint to the table.
                INSERT INTO keywords (keyword, id_text)
                VALUES (trim(keyword_text), v_text_id);
            END IF;
        END LOOP;
    END IF;

END;
$$ LANGUAGE plpgsql;
