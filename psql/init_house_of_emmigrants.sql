-- 1
CREATE TABLE users (
  id_user      SERIAL      PRIMARY KEY,
  username     TEXT        NOT NULL,
  email        TEXT        NOT NULL,
  password     TEXT        NOT NULL,
  register_at  TIMESTAMP   NOT NULL
);

CREATE TABLE sexes (
  id_sex SERIAL PRIMARY KEY,
  sex TEXT NOT NULL
);

CREATE TABLE marital_statuses (
  id_marital SERIAL PRIMARY KEY,
  status TEXT NOT NULL
);

CREATE TABLE legal_statuses (
  id_legal SERIAL PRIMARY KEY,
  status TEXT NOT NULL
);

CREATE TABLE travel_types (
  id_type SERIAL PRIMARY KEY,
  type TEXT NOT NULL
);

CREATE TABLE ports (
  id_port SERIAL PRIMARY KEY,
  port TEXT NOT NULL
);

CREATE TABLE relationships (
  id_relationship SERIAL PRIMARY KEY,
  relationship_type TEXT NOT NULL
);

CREATE TABLE cultures (
  id_culture SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT
);

CREATE TABLE languages (
  id_language SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE cultural_events (
  id_event SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  event_data TEXT
);

CREATE TABLE cultural_practices (
  id_practice SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT
);

CREATE TABLE medical_treatments (
  id_treatment SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT
);

CREATE TABLE church_affiliations (
  id_affiliation SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE social_activities (
  id_activity SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE involvement_types (
  id_involvement SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE education_levels (
  id_education SERIAL PRIMARY KEY,
  level TEXT NOT NULL
);

CREATE TABLE schools (
  id_school SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE communities (
  id_community SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NULL
);

CREATE TABLE countries (
  id_country SERIAL PRIMARY KEY,
  country TEXT NOT NULL
);

CREATE TABLE historic_events (
  id_event SERIAL PRIMARY KEY,
  historic_event TEXT NULL
);

CREATE TABLE administrators (
  id_administrator SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  FOREIGN KEY (id_administrator) REFERENCES users(id_user)
);

CREATE TABLE cities (
  id_city    SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_country INT NULL,
  city       TEXT NOT NULL,
  FOREIGN KEY (id_country) REFERENCES countries(id_country)
);

CREATE TABLE people (
  id_people SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  name TEXT NULL,
  birthday DATE NULL,
  birthplace_city INT NULL REFERENCES cities(id_city),
  birthplace_country INT NULL REFERENCES countries(id_country),
  sex INT NULL REFERENCES sexes(id_sex),
  marital_status INT NULL REFERENCES marital_statuses(id_marital),
  legal_status INT NULL REFERENCES legal_statuses(id_legal)
  );

CREATE TABLE health (
  id_health    SERIAL    PRIMARY KEY, -- Changed from INT to SERIAL
  id_people    INT       NOT NULL,
  health_issue TEXT      NOT NULL,
  death_cause  BOOLEAN   NOT NULL,
  FOREIGN KEY (id_people) REFERENCES people(id_people)
);

CREATE TABLE jobs (
  id_job SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_people INT NOT NULL,
  occupation TEXT NULL,
  employer TEXT NULL,
  job_position TEXT NULL,
  education_level INT NULL,
  FOREIGN KEY (id_people) REFERENCES people(id_people),
  FOREIGN KEY (education_level) REFERENCES education_levels(id_education)
);


CREATE TABLE text_files (
  id_text SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_people INT NOT NULL,
  filename TEXT NOT NULL,
  interview_location TEXT NULL,
  interview_date DATE NULL,
  story_title TEXT NOT NULL,
  story_summary TEXT NOT NULL,
  FOREIGN KEY (id_people) REFERENCES people(id_people)
);

CREATE TABLE immigrations (
  id_immigration SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  immigration_date DATE NULL,
  reason_immigration TEXT NULL,
  id_people INT NOT NULL,
  origin_city_id INT NULL,
  origin_country_id INT NULL,
  destination_city_id  INT NULL,
  destination_country_id INT NULL,
  travel_type_id       INT NULL,
  entry_port_id        INT NULL,
  arrival_port_id      INT NULL,
  return_plans         TEXT NULL,
  FOREIGN KEY (id_people)
    REFERENCES people(id_people),
  FOREIGN KEY (origin_city_id)
    REFERENCES cities(id_city),
  FOREIGN KEY (origin_country_id)
    REFERENCES countries(id_country),
  FOREIGN KEY (destination_city_id)
    REFERENCES cities(id_city),
  FOREIGN KEY (destination_country_id)
    REFERENCES countries(id_country),
  FOREIGN KEY (travel_type_id)
    REFERENCES travel_types(id_type),
  FOREIGN KEY (entry_port_id)
    REFERENCES ports(id_port),
  FOREIGN KEY (arrival_port_id)
    REFERENCES ports(id_port)
);

CREATE TABLE people_cultures (
  id_people INT NOT NULL,
  id_culture INT NOT NULL,
  PRIMARY KEY (id_people, id_culture), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_people)  REFERENCES people(id_people),
  FOREIGN KEY (id_culture) REFERENCES cultures(id_culture)
);


CREATE TABLE notes_excerpts (
  id_note SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_text INT NOT NULL,
  notes TEXT NULL,
  FOREIGN KEY (id_text) REFERENCES text_files(id_text)
);

CREATE TABLE image_files (
  id_image SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_people INT NOT NULL,
  filename TEXT NOT NULL,
  image_description TEXT NULL,
  FOREIGN KEY (id_people)
    REFERENCES people(id_people)
);


CREATE TABLE graphics (
  id_graphic SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_text INT NOT NULL,
  graphic_type TEXT NULL,
  graphic_data TEXT NULL,
  FOREIGN KEY (id_text) REFERENCES text_files(id_text)
);

CREATE TABLE passwords_resets (
  id_reset SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  user_id INT NOT NULL,
  reset_token TEXT NOT NULL,
  requested_at TIMESTAMP  NOT NULL,
  expires_at TIMESTAMP  NOT NULL,
  used_at TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(id_user)
);

CREATE TABLE keywords (
  id_keyword SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  keyword TEXT NOT NULL,
  id_text INT NOT NULL,
  FOREIGN KEY (id_text) REFERENCES text_files(id_text)
);

CREATE TABLE text_image_link (
  id_text  INT NOT NULL,
  id_img   INT NOT NULL,
  PRIMARY KEY (id_text, id_img), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_text) REFERENCES text_files(id_text),
  FOREIGN KEY (id_img)  REFERENCES image_files(id_image)
);

CREATE TABLE people_in_historic_events (
  id_people  INT NOT NULL,
  id_event   INT NOT NULL,
  PRIMARY KEY (id_people, id_event), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_people) REFERENCES people(id_people),
  FOREIGN KEY (id_event)  REFERENCES historic_events(id_event)
);


CREATE TABLE people_relationships (
  id_people INT NOT NULL,
  id_relative INT NOT NULL,
  id_type INT NOT NULL,
  PRIMARY KEY(id_people, id_relative), -- Composite PK, not changed to SERIAL
  FOREIGN KEY(id_type) REFERENCES relationships(id_relationship),
  FOREIGN KEY(id_people) REFERENCES people(id_people),
  FOREIGN KEY(id_relative) REFERENCES people(id_people)
);

CREATE TABLE treatments (
  id_health    INT NOT NULL,
  id_treatment INT NOT NULL,
  PRIMARY KEY (id_health, id_treatment), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_health)     REFERENCES health(id_health),
  FOREIGN KEY (id_treatment) REFERENCES medical_treatments(id_treatment)
);

CREATE TABLE community_memberships (
  id_community INT NOT NULL,
  id_people    INT NOT NULL,
  joined_at DATE NULL,
  PRIMARY KEY(id_community, id_people), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_community) REFERENCES communities(id_community),
  FOREIGN KEY (id_people) REFERENCES people(id_people)
);

CREATE TABLE membership_churches (
  id_community INT NOT NULL,
  id_people INT NOT NULL,
  id_affiliation INT NOT NULL,
  PRIMARY KEY (id_community, id_people, id_affiliation), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_community) REFERENCES communities(id_community),
  FOREIGN KEY (id_people) REFERENCES people(id_people),
  FOREIGN KEY (id_affiliation) REFERENCES church_affiliations(id_affiliation)
);

CREATE TABLE membership_activities (
  id_community INT NOT NULL,
  id_people    INT NOT NULL,
  id_activity  INT NOT NULL,
  PRIMARY KEY (id_community, id_people, id_activity), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_community) REFERENCES communities(id_community),
  FOREIGN KEY (id_people)    REFERENCES people(id_people),
  FOREIGN KEY (id_activity)  REFERENCES social_activities(id_activity)
);

CREATE TABLE membership_involvements (
  id_community    INT NOT NULL,
  id_people       INT NOT NULL,
  id_involvement  INT NOT NULL,
  PRIMARY KEY (id_community, id_people, id_involvement), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_community)   REFERENCES communities(id_community),
  FOREIGN KEY (id_people)      REFERENCES people(id_people),
  FOREIGN KEY (id_involvement) REFERENCES involvement_types(id_involvement)
);


CREATE TABLE culture_languages (
  id_culture  INT NOT NULL,
  id_language INT NOT NULL,
  PRIMARY KEY (id_culture, id_language), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_culture)  REFERENCES cultures(id_culture),
  FOREIGN KEY (id_language) REFERENCES languages(id_language)
);

CREATE TABLE culture_practices_map (
  id_culture  INT NOT NULL,
  id_practice INT NOT NULL,
  PRIMARY KEY (id_culture, id_practice), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_culture)  REFERENCES cultures(id_culture),
  FOREIGN KEY (id_practice) REFERENCES cultural_practices(id_practice)
);

CREATE TABLE culture_events_map (
  id_culture INT NOT NULL,
  id_event   INT NOT NULL,
  PRIMARY KEY (id_culture, id_event), -- Composite PK, not changed to SERIAL
  FOREIGN KEY (id_culture) REFERENCES cultures(id_culture),
  FOREIGN KEY (id_event)   REFERENCES cultural_events(id_event)
);

CREATE TABLE person_education (
  id_person_education SERIAL PRIMARY KEY, -- Changed from INT to SERIAL
  id_people INT NOT NULL,
  id_school INT NOT NULL,
  id_education_level INT NOT NULL,
  graduation_year TEXT,
  FOREIGN KEY (id_people) REFERENCES people(id_people),
  FOREIGN KEY (id_school) REFERENCES schools(id_school),
  FOREIGN KEY (id_education_level) REFERENCES education_levels(id_education)
);
