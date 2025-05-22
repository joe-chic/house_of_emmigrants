-- Procedure 1: Timeline of Emigration Departure Dates (same as before)
CREATE OR REPLACE PROCEDURE get_emigration_departure_timeline_proc(
    p_timeline_cursor INOUT REFCURSOR
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_timeline_cursor FOR
        SELECT
            EXTRACT(YEAR FROM ti.departure_date)::INTEGER AS departure_year,
            COUNT(*) AS story_count -- Assuming one travel_info record per story for this count
        FROM
            travel_info ti -- Querying travel_info directly as per your new main.py
        WHERE
            ti.departure_date IS NOT NULL
        GROUP BY
            departure_year
        ORDER BY
            departure_year ASC;
END;
$$;

-- Procedure 2: Top Keywords (similar to before, but queries 'keywords' table directly)
CREATE OR REPLACE PROCEDURE get_top_salient_keywords_proc(
    p_keywords_cursor INOUT REFCURSOR,
    p_limit_val IN INTEGER
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_keywords_cursor FOR
        SELECT
            k.keyword AS keyword_text,
            COUNT(*) AS frequency
        FROM
            keywords k
        GROUP BY
            keyword_text
        ORDER BY
            frequency DESC, keyword_text ASC
        LIMIT p_limit_val;
END;
$$;

-- Procedure 3: Geographic Distribution (Destination Cities)
CREATE OR REPLACE PROCEDURE get_destination_city_distribution_proc(
    p_dest_city_cursor INOUT REFCURSOR
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_dest_city_cursor FOR
        SELECT
            c.city AS destination_city_name, -- Changed alias for clarity
            COUNT(*) AS story_count -- Assuming one travel_info record links to one city for this count
        FROM
            travel_info ti
        JOIN
            cities c ON ti.destination_city = c.id_city
        GROUP BY
            c.city
        ORDER BY
            story_count DESC, destination_city_name ASC; -- Order by new alias
END;
$$;

-- Procedure 4: Recent Stories with Full Details
CREATE OR REPLACE PROCEDURE get_recent_stories_details_proc(
    p_recent_stories_cursor INOUT REFCURSOR,
    p_limit_val IN INTEGER -- Added limit for "recent"
)
LANGUAGE plpgsql AS $$
BEGIN
    OPEN p_recent_stories_cursor FOR
        SELECT
          tf.story_title,
          tf.story_summary,
          pi_main.first_name   AS main_first,
          pi_main.first_surname AS main_last,
          s.sex,
          ms.status           AS marital_status,
          el.level            AS education_level,
          ls.status           AS legal_status,
          -- Using COALESCE with ARRAY_AGG and FILTER for cleaner empty arrays
          COALESCE(ARRAY_AGG(DISTINCT pi_ment.first_name || ' ' || pi_ment.first_surname)
            FILTER (WHERE pi_ment.id_person IS NOT NULL), ARRAY[]::TEXT[]) AS mentions,
          ti.departure_date,
          c.city              AS destination_city_name, -- Aliased for clarity
          co.country          AS destination_country_name, -- Aliased for clarity
          mm.motive,
          ti.travel_duration,
          ti.return_plans,
          -- Using COALESCE with ARRAY_AGG and FILTER for cleaner empty arrays
          COALESCE(ARRAY_AGG(DISTINCT tm.method)
            FILTER (WHERE tm.id_travel_method IS NOT NULL), ARRAY[]::TEXT[]) AS methods,
          tf.id_text -- For potential ordering or identification
        FROM text_files tf
        LEFT JOIN demographic_info di ON tf.id_demography = di.id_demography
        LEFT JOIN person_info pi_main ON di.id_main_person = pi_main.id_person
        LEFT JOIN sexes s ON di.id_sex = s.id_sex
        LEFT JOIN marital_statuses ms ON di.id_marital = ms.id_marital
        LEFT JOIN education_levels el ON di.id_education = el.id_education
        LEFT JOIN legal_statuses ls ON di.id_legal = ls.id_legal
        LEFT JOIN mention_link ml ON tf.id_demography = ml.id_demography -- Should this be di.id_demography? Check schema. Assuming di.
        LEFT JOIN person_info pi_ment ON ml.id_person = pi_ment.id_person
        LEFT JOIN travel_info ti ON tf.id_travel = ti.id_travel
        LEFT JOIN cities c ON ti.destination_city = c.id_city
        LEFT JOIN countries co ON c.id_country = co.id_country
        LEFT JOIN motives_migration mm ON ti.id_motive_migration = mm.id_motive
        LEFT JOIN travel_link tl ON ti.id_travel = tl.id_travel
        LEFT JOIN travel_methods tm ON tl.id_travel_method = tm.id_travel_method
        GROUP BY
          tf.id_text, -- Group by primary key of text_files for correct aggregation per story
          pi_main.id_person, s.id_sex, ms.id_marital, el.id_education, ls.id_legal, -- Group by FKs
          ti.id_travel, c.id_city, co.id_country, mm.id_motive -- Group by FKs
          -- Ensure all non-aggregated selected columns from the main tables (tf, pi_main, s, ms etc.) are in GROUP BY
          -- or are functionally dependent on the GROUP BY columns.
          -- tf.story_title, tf.story_summary, pi_main.first_name, pi_main.first_surname, s.sex, ms.status, el.level, ls.status,
          -- ti.departure_date, c.city, co.country, mm.motive, ti.travel_duration, ti.return_plans
        ORDER BY 
          ti.departure_date DESC NULLS LAST, tf.id_text DESC -- Order by departure date, then by id_text
        LIMIT p_limit_val;
END;
$$;
