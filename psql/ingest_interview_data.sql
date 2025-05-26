CREATE OR REPLACE PROCEDURE ingest_interview_from_ai_json_v2(
    -- I. Interview Meta-Information
    p_text_filename TEXT,
    p_story_title TEXT,
    p_story_summary TEXT,
    p_interview_location TEXT,
    p_interview_date TEXT,

    -- II. Primary Interviewee Information
    p_interviewee_name TEXT,
    p_interviewee_birthday TEXT,
    p_interviewee_birthplace_city_name TEXT,
    p_interviewee_birthplace_country_name TEXT,
    p_interviewee_sex TEXT,
    p_interviewee_marital_status TEXT,
    p_interviewee_legal_status TEXT,

    -- III. Interviewee's Immigration Event(s)
    p_immigration_events JSONB, -- Array of immigration event objects

    -- IV. Interviewee's Job(s)
    p_jobs JSONB, -- Array of job objects

    -- V. Interviewee's Education
    p_education_history JSONB, -- Array of education objects

    -- VI. Health - Placeholder
    p_health_issues JSONB, -- Array of health issue objects

    -- VII. Other People Mentioned
    p_other_people_mentioned JSONB,

    -- VIII. Community - Placeholder
    p_community_involvements JSONB,

    -- IX. Cultural Aspects
    p_cultural_associated_cultures TEXT[],
    p_cultural_languages_spoken JSONB,
    p_cultural_events_mentioned JSONB, -- Array of cultural event objects
    p_cultural_practices_mentioned JSONB, -- Array of cultural practice objects


    -- X. Historic Event Involvement
    p_historic_events_involved JSONB,

    -- XI. General Keywords
    p_general_keywords TEXT[]
)
LANGUAGE plpgsql AS $$
DECLARE
    v_interviewee_id INT;
    v_text_file_id INT;
    v_parsed_interview_date DATE;

    -- Loop variables for arrays
    imm_event RECORD;
    v_imm_origin_country_id INT;
    v_imm_origin_city_id INT;
    v_imm_dest_country_id INT;
    v_imm_dest_city_id INT;
    v_imm_travel_type_id INT;
    v_imm_entry_port_id INT;
    v_imm_arrival_port_id INT;
    v_parsed_imm_date DATE;

    job_record RECORD;
    v_job_edu_level_id INT;

    edu_record RECORD;
    v_edu_school_id INT;
    v_edu_level_id INT;
    
    other_person_record RECORD;
    v_other_person_id INT;
    v_relationship_id INT;

    culture_name_item TEXT;
    v_culture_id INT;

    language_record RECORD;
    v_language_id INT;
    v_person_main_culture_id INT; -- To link language if no specific culture context

    historic_event_record RECORD;
    v_historic_event_id INT;

    keyword_item TEXT;
    
    -- Placeholder for more complex loops
    health_record RECORD;
    treatment_record RECORD;
    community_record RECORD;
    social_activity_item TEXT;
    cultural_event_record RECORD;
    cultural_practice_record RECORD;


BEGIN
    -- === II. Create/Find Primary Interviewee ===
    v_interviewee_id := find_or_create_person(
        p_full_name := p_interviewee_name,
        p_birthday := p_interviewee_birthday,
        p_birthplace_city_name := p_interviewee_birthplace_city_name,
        p_birthplace_country_name := p_interviewee_birthplace_country_name,
        p_sex_name := p_interviewee_sex,
        p_marital_status_name := p_interviewee_marital_status,
        p_legal_status_name := p_interviewee_legal_status
    );

    IF v_interviewee_id IS NULL THEN
        RAISE NOTICE 'Failed to create or find primary interviewee: %', p_interviewee_name;
        RETURN; -- Exit if no primary interviewee
    END IF;

    -- === I. Insert Text File Meta-Information ===
    BEGIN v_parsed_interview_date := p_interview_date::DATE; EXCEPTION WHEN OTHERS THEN v_parsed_interview_date := NULL; END;
    
    INSERT INTO text_files (id_people, filename, interview_location, interview_date, story_title, story_summary)
    VALUES (v_interviewee_id, p_text_filename, p_interview_location, v_parsed_interview_date, p_story_title, p_story_summary)
    RETURNING id_text INTO v_text_file_id;

    -- === III. Insert Immigration Event(s) for Interviewee ===
    IF p_immigration_events IS NOT NULL AND jsonb_array_length(p_immigration_events) > 0 THEN
        FOR imm_event IN SELECT * FROM jsonb_to_recordset(p_immigration_events) AS x(
            immigration_date TEXT, reason_immigration TEXT,
            origin_city_name TEXT, origin_country_name TEXT,
            destination_city_name TEXT, destination_country_name TEXT,
            travel_type_name TEXT, entry_port_name TEXT, arrival_port_name TEXT,
            return_plans TEXT
        ) LOOP
            BEGIN v_parsed_imm_date := imm_event.immigration_date::DATE; EXCEPTION WHEN OTHERS THEN v_parsed_imm_date := NULL; END;
            
            v_imm_origin_country_id := get_country_id_by_name(imm_event.origin_country_name, TRUE);
            v_imm_origin_city_id := get_city_id_by_name(imm_event.origin_city_name, v_imm_origin_country_id, TRUE);

            v_imm_dest_country_id := get_country_id_by_name(imm_event.destination_country_name, TRUE);
            v_imm_dest_city_id := get_city_id_by_name(imm_event.destination_city_name, v_imm_dest_country_id, TRUE);
            
            v_imm_travel_type_id := get_travel_type_id_by_name(imm_event.travel_type_name, TRUE);
            -- TODO: Add get_port_id_by_name for entry_port_name and arrival_port_name
            -- v_imm_entry_port_id := get_port_id_by_name(imm_event.entry_port_name, TRUE);
            -- v_imm_arrival_port_id := get_port_id_by_name(imm_event.arrival_port_name, TRUE);

            INSERT INTO immigrations (
                immigration_date, reason_immigration, id_people,
                origin_city_id, origin_country_id, destination_city_id, destination_country_id,
                travel_type_id, entry_port_id, arrival_port_id, return_plans
            ) VALUES (
                v_parsed_imm_date, imm_event.reason_immigration, v_interviewee_id,
                v_imm_origin_city_id, v_imm_origin_country_id, v_imm_dest_city_id, v_imm_dest_country_id,
                v_imm_travel_type_id, v_imm_entry_port_id, v_imm_arrival_port_id, imm_event.return_plans
            );
        END LOOP;
    END IF;

    -- === IV. Insert Job(s) for Interviewee ===
    IF p_jobs IS NOT NULL AND jsonb_array_length(p_jobs) > 0 THEN
        FOR job_record IN SELECT * FROM jsonb_to_recordset(p_jobs) AS x(
            occupation TEXT, employer TEXT, job_position TEXT, education_level_for_job TEXT
        ) LOOP
            v_job_edu_level_id := get_education_level_id_by_name(job_record.education_level_for_job);
            INSERT INTO jobs (id_people, occupation, employer, job_position, education_level)
            VALUES (v_interviewee_id, job_record.occupation, job_record.employer, job_record.job_position, v_job_edu_level_id);
        END LOOP;
    END IF;

    -- === V. Insert Education History for Interviewee ===
    IF p_education_history IS NOT NULL AND jsonb_array_length(p_education_history) > 0 THEN
        FOR edu_record IN SELECT * FROM jsonb_to_recordset(p_education_history) AS x(
            school_name TEXT, education_level_achieved TEXT, graduation_year TEXT
        ) LOOP
            v_edu_school_id := get_school_id_by_name(edu_record.school_name, TRUE);
            v_edu_level_id := get_education_level_id_by_name(edu_record.education_level_achieved);
            -- Only insert if we have a valid education level ID. School can be optional if schema allows.
            IF v_edu_level_id IS NOT NULL THEN 
                 -- If school_id is required by DB, ensure v_edu_school_id is also NOT NULL
                IF v_edu_school_id IS NOT NULL THEN
                    INSERT INTO person_education (id_people, id_school, id_education_level, graduation_year)
                    VALUES (v_interviewee_id, v_edu_school_id, v_edu_level_id, edu_record.graduation_year);
                ELSE
                    RAISE NOTICE 'Skipping education record for interviewee % due to missing school: %', v_interviewee_id, edu_record.school_name;
                END IF;
            END IF;
        END LOOP;
    END IF;
    
    -- === VII. Insert Other People Mentioned and Relationships ===
    IF p_other_people_mentioned IS NOT NULL AND jsonb_array_length(p_other_people_mentioned) > 0 THEN
        FOR other_person_record IN SELECT * FROM jsonb_to_recordset(p_other_people_mentioned) AS x(full_name TEXT, relationship_to_interviewee TEXT, details TEXT) LOOP
            IF other_person_record.full_name IS NOT NULL AND other_person_record.full_name <> '' THEN
                v_other_person_id := find_or_create_person(other_person_record.full_name); 
                
                IF v_other_person_id IS NOT NULL AND v_interviewee_id <> v_other_person_id THEN
                    v_relationship_id := get_relationship_id_by_name(other_person_record.relationship_to_interviewee, TRUE);
                    IF v_relationship_id IS NOT NULL THEN
                        INSERT INTO people_relationships (id_people, id_relative, id_type)
                        VALUES (v_interviewee_id, v_other_person_id, v_relationship_id)
                        ON CONFLICT (id_people, id_relative) DO NOTHING;
                    END IF;
                END IF;
            END IF;
        END LOOP;
    END IF;

    -- === IX. Cultural Aspects ===
    IF p_cultural_associated_cultures IS NOT NULL THEN
        FOREACH culture_name_item IN ARRAY p_cultural_associated_cultures LOOP
            v_culture_id := get_culture_id_by_name(culture_name_item, TRUE);
            IF v_culture_id IS NOT NULL THEN
                INSERT INTO people_cultures (id_people, id_culture)
                VALUES (v_interviewee_id, v_culture_id)
                ON CONFLICT (id_people, id_culture) DO NOTHING;
                IF v_person_main_culture_id IS NULL THEN v_person_main_culture_id := v_culture_id; END IF; -- Capture one for language linking
            END IF;
        END LOOP;
    END IF;

    IF p_cultural_languages_spoken IS NOT NULL AND jsonb_array_length(p_cultural_languages_spoken) > 0 THEN
        FOR language_record IN SELECT * FROM jsonb_to_recordset(p_cultural_languages_spoken) AS x(language_name TEXT, proficiency_or_context TEXT) LOOP
            v_language_id := get_language_id_by_name(language_record.language_name, TRUE);
            IF v_language_id IS NOT NULL AND v_person_main_culture_id IS NOT NULL THEN
                 INSERT INTO culture_languages (id_culture, id_language)
                 VALUES (v_person_main_culture_id, v_language_id) -- Links language to one of the person's cultures
                 ON CONFLICT (id_culture, id_language) DO NOTHING;
            END IF;
        END LOOP;
    END IF;
    
    -- Cultural Events Mentioned
    IF p_cultural_events_mentioned IS NOT NULL AND jsonb_array_length(p_cultural_events_mentioned) > 0 THEN
        FOR cultural_event_record IN SELECT * FROM jsonb_to_recordset(p_cultural_events_mentioned) AS x(event_name TEXT, event_details TEXT) LOOP
            -- TODO: Create get_cultural_event_id_by_name helper
            -- v_cultural_event_id := get_cultural_event_id_by_name(cultural_event_record.event_name, TRUE);
            -- IF v_cultural_event_id IS NOT NULL AND v_person_main_culture_id IS NOT NULL THEN
            --     INSERT INTO culture_events_map (id_culture, id_event)
            --     VALUES (v_person_main_culture_id, v_cultural_event_id)
            --     ON CONFLICT (id_culture, id_event) DO NOTHING;
            -- END IF;
        END LOOP;
    END IF;

    -- Cultural Practices Mentioned
    IF p_cultural_practices_mentioned IS NOT NULL AND jsonb_array_length(p_cultural_practices_mentioned) > 0 THEN
        FOR cultural_practice_record IN SELECT * FROM jsonb_to_recordset(p_cultural_practices_mentioned) AS x(practice_name TEXT, practice_description TEXT) LOOP
            -- TODO: Create get_cultural_practice_id_by_name helper
            -- v_cultural_practice_id := get_cultural_practice_id_by_name(cultural_practice_record.practice_name, TRUE);
            -- IF v_cultural_practice_id IS NOT NULL AND v_person_main_culture_id IS NOT NULL THEN
            --     INSERT INTO culture_practices_map (id_culture, id_practice)
            --     VALUES (v_person_main_culture_id, v_cultural_practice_id)
            --     ON CONFLICT (id_culture, id_practice) DO NOTHING;
            -- END IF;
        END LOOP;
    END IF;


    -- === X. Historic Event Involvement ===
    IF p_historic_events_involved IS NOT NULL AND jsonb_array_length(p_historic_events_involved) > 0 THEN
        FOR historic_event_record IN SELECT * FROM jsonb_to_recordset(p_historic_events_involved) AS x(historic_event_name TEXT, role_or_involvement_description TEXT) LOOP
            v_historic_event_id := get_historic_event_id_by_name(historic_event_record.historic_event_name, TRUE);
            IF v_historic_event_id IS NOT NULL THEN
                INSERT INTO people_in_historic_events (id_people, id_event)
                VALUES (v_interviewee_id, v_historic_event_id)
                ON CONFLICT (id_people, id_event) DO NOTHING;
            END IF;
        END LOOP;
    END IF;

    -- === XI. General Keywords ===
    IF v_text_file_id IS NOT NULL AND p_general_keywords IS NOT NULL THEN
        FOREACH keyword_item IN ARRAY p_general_keywords LOOP
            IF keyword_item IS NOT NULL AND keyword_item <> '' THEN
                -- Consider unique constraint on (keyword, id_text) in keywords table
                INSERT INTO keywords (keyword, id_text)
                VALUES (trim(keyword_item), v_text_file_id)
                ON CONFLICT DO NOTHING; -- Requires a unique constraint on (keyword, id_text) to work
            END IF;
        END LOOP;
    END IF;

    -- Sections requiring more detailed JSON from AI and dedicated loops (not fully implemented here):
    -- VI. Health Issues (p_health_issues JSONB)
    -- VIII. Community Involvements (p_community_involvements JSONB)

END;
$$;
