SELECT
          tf.story_title,
          tf.story_summary,
          -- Demographic for main interviewee
          pi_main.first_name   AS main_first,
          pi_main.first_surname AS main_last,
          s.sex,
          ms.status           AS marital_status,
          el.level            AS education_level,
          ls.status           AS legal_status,
          -- Mentioned people names
          ARRAY_AGG(pi_ment.first_name || ' ' || pi_ment.first_surname) 
            FILTER (WHERE pi_ment.id_person IS NOT NULL) AS mentions,
          -- Travel info
          ti.departure_date,
          c.city              AS destination_city,
          co.country          AS destination_country,
          mm.motive,
          ti.travel_duration,
          ti.return_plans,
          ARRAY_AGG(tm.method) AS methods
        FROM text_files tf
        -- link main person
        LEFT JOIN demographic_info di ON tf.id_demography = di.id_demography
        LEFT JOIN person_info pi_main ON di.id_main_person = pi_main.id_person
        LEFT JOIN sexes s ON di.id_sex = s.id_sex
        LEFT JOIN marital_statuses ms ON di.id_marital = ms.id_marital
        LEFT JOIN education_levels el ON di.id_education = el.id_education
        LEFT JOIN legal_statuses ls ON di.id_legal = ls.id_legal
        -- mentioned people
        LEFT JOIN mention_link ml ON tf.id_demography = ml.id_demography
        LEFT JOIN person_info pi_ment ON ml.id_person = pi_ment.id_person
        -- travel info
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