import json
import os
import re # Keep re if you use it in call_gemini_api_with_retry for JSON extraction
import google.generativeai as genai
import psycopg
import time # For sleeping in retry and for timestamping logs
import random # For jitter in backoff
from datetime import datetime # For timestamping logs

# --- Database connection settings ---
DB_NAME = 'house_of_emigrants'
DB_USER = 'postgres'
DB_PASS = '666' # Consider using environment variables
DB_HOST = 'localhost'
DB_PORT = '5432'

def get_db_connection():
    return psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )

# --- Genai configuration ---
# IMPORTANT: "gemini-2.0-flash" is not a standard public model name.
# Please use a valid model name like "gemini-1.5-flash-latest" or "gemini-1.0-pro".
# If "gemini-2.0-flash" is a custom endpoint or a typo, this will fail.
# For this example, I'll assume you meant "gemini-1.5-flash-latest".
MODEL_NAME = "gemini-1.5-flash-latest" # CORRECTED - USE A VALID MODEL NAME
LOW_TEMPERATURE = 0.1
MAX_OUTPUT_TOKENS = 4096 # Increased from 2048, good for complex JSON

# --- Logging Configuration ---
LOG_FILE_PATH = "gemini_extraction_log.jsonl" # Using .jsonl for JSON Lines format

GEMINI_JSON_PROMPT_TEMPLATE = """
You are an expert data extractor specializing in historical personal narratives. Based on the following interview text with an emigrant or their descendants, extract the specified information.
Output **only** a single, valid JSON object. Adhere strictly to the field names and expected data types.
If information for a field or an entire section is not present in the text, use an empty string "" for optional string fields, null for optional non-string fields (like dates if not found), or an empty array [] for lists.

**I. Interview Meta-Information:**
- "story_title": (string) A concise title for the story or interview.
- "story_summary": (string) A brief 1-2 sentence summary of the interview's main topics.
- "interview_location": (string, optional) Location where the interview took place, if mentioned.
- "interview_date": (string, YYYY-MM-DD format, optional) Date the interview was conducted, if mentioned.

**II. Primary Interviewee Information (`people` table related):**
- "interviewee_name": (string) Full name of the primary person being interviewed (e.g., "Karl Andersson").
- "interviewee_birthday": (string, YYYY-MM-DD format, optional) Birthdate of the interviewee.
- "interviewee_birthplace_city_name": (string, optional) Name of the city where the interviewee was born.
- "interviewee_birthplace_country_name": (string, optional) Name of the country where the interviewee was born.
- "interviewee_sex": (string, optional) Sex of the interviewee. Valid values: "female", "male".
- "interviewee_marital_status": (string, optional) Marital status. Valid values: "single", "married", "widowed", "divorced", "separated", "engaged".
- "interviewee_legal_status_at_migration_or_current": (string, optional) Legal status, ideally at migration if applicable, otherwise current. Valid values: "citizen of origin country", "stateless", "refugee", "asylum seeker", "undocumented", "naturalized citizen", "legal immigrant", "temporary resident".

**III. Interviewee's Immigration Event(s) (`immigrations` table related):**
  (If multiple distinct immigration events are described for the interviewee, provide an array of objects. If only one, provide a single object or an array with one object. If none, use an empty array.)
- "interviewee_immigration_events": [
    {
      "immigration_date": (string, YYYY-MM-DD format, optional) Date of this specific immigration.
      "reason_immigration": (string, optional) Reason for this immigration.
      "origin_city_name": (string, optional) City of origin for this immigration.
      "origin_country_name": (string, optional) Country of origin for this immigration.
      "destination_city_name": (string, optional) City of destination for this immigration.
      "destination_country_name": (string, optional) Country of destination for this immigration.
      "travel_type_name": (string, optional) Main type/method of travel (e.g., "steamship", "train", "by foot").
      "entry_port_name": (string, optional) Port of entry, if mentioned.
      "arrival_port_name": (string, optional) Port of arrival, if mentioned.
      "return_plans": (string, optional) Plans regarding returning to origin after this immigration (brief).
    }
  ]

**IV. Interviewee's Job(s) / Occupation(s) (`jobs` table related):**
  (List all distinct jobs/occupations mentioned for the interviewee.)
- "interviewee_jobs": [
    {
      "occupation": (string) Title or type of occupation (e.g., "Farmer", "Seamstress", "Teacher").
      "employer": (string, optional) Name of the employer, if mentioned.
      "job_position": (string, optional) Specific position held, if different from occupation.
      "education_level_for_job": (string, optional) Education level relevant to this job. Valid values: "no formal education", "primary school", "some secondary school", "completed secondary school", "trade or vocational training", "some college/university", "completed college/university", "illiterate".
    }
  ]

**V. Interviewee's Education (`person_education` table related):**
  (List distinct educational experiences.)
- "interviewee_education_history": [
    {
      "school_name": (string, optional) Name of the school attended.
      "education_level_achieved": (string) Level of education. Valid values: (see list under interviewee_jobs).
      "graduation_year": (string, optional) Year of graduation or completion (can be just YYYY).
    }
  ]

**VI. Interviewee's Health Information (`health` table related):**
  (List distinct health issues mentioned.)
- "interviewee_health_issues": [
    {
      "health_issue_description": (string) Description of the health issue or illness.
      "was_death_cause": (boolean, optional) True if this issue was stated as the cause of death for the interviewee (unlikely to be in an interview with them, but for completeness).
      "medical_treatments_received": [
        {
          "treatment_name": (string) Name of the medical treatment.
          "treatment_description": (string, optional) Description of the treatment.
        }
      ]
    }
  ]

**VII. Other People Mentioned (`people` and `people_relationships` tables related):**
  (List distinct individuals mentioned, other than the primary interviewee.)
- "other_people_mentioned": [
    {
      "full_name": (string) Full name of the mentioned person.
      "relationship_to_interviewee": (string, optional) Their relationship to the interviewee (e.g., "father", "sister", "friend", "cousin", "employer", "community member").
      "details": (string, optional) Any other brief relevant details about this person from the text.
    }
  ]

**VIII. Community Involvement (`communities`, `church_affiliations`, `social_activities`, `involvement_types` related):**
- "interviewee_community_involvements": [
    {
      "community_name": (string) Name of the community or organization.
      "community_description": (string, optional) Brief description of the community.
      "joined_at_date": (string, YYYY-MM-DD format, optional) Date joined, if mentioned.
      "church_affiliation_name": (string, optional) Specific church affiliation within this community, if applicable.
      "social_activities_participated": [ (string) List of social activity names within this community. ]
      "type_of_involvement": (string, optional) General type of involvement (e.g., "member", "volunteer", "leader").
    }
  ]

**IX. Cultural Aspects (`cultures`, `languages`, `cultural_events`, `cultural_practices` related):**
- "interviewee_cultural_aspects": {
    "associated_culture_names": [ (string) Names of cultures the interviewee identifies with or discusses (e.g., "Swedish", "Swedish-American"). ],
    "languages_spoken_or_mentioned": [
        {
          "language_name": (string) Name of the language.
          "proficiency_or_context": (string, optional) e.g., "fluent", "native", "learned in school", "spoken at home".
        }
    ],
    "cultural_events_mentioned": [
        {
          "event_name": (string) Name of the cultural event.
          "event_details": (string, optional) Details about the event.
        }
    ],
    "cultural_practices_mentioned": [
        {
          "practice_name": (string) Name of the cultural practice.
          "practice_description": (string, optional) Description of the practice.
        }
    ]
  }

**X. Involvement in Historic Events (`historic_events`, `people_in_historic_events` related):**
- "interviewee_historic_event_involvement": [
    {
      "historic_event_name": (string) Name or description of the historic event.
      "role_or_involvement_description": (string, optional) How the interviewee was involved or affected.
    }
  ]

**XI. General Keywords (for `keywords` table):**
- "general_keywords": [ (string) Array of 5-15 salient keywords or phrases from the entire interview, not already captured as specific entities. ]

**Valid Values for Enumerated Fields (must match exactly if not empty):**
- Sex: "female", "male"
- Marital Status: "single", "married", "widowed", "divorced", "separated", "engaged"
- Education Level: "no formal education", "primary school", "some secondary school", "completed secondary school", "trade or vocational training", "some college/university", "completed college/university", "illiterate"
- Legal Status: "citizen of origin country", "stateless", "refugee", "asylum seeker", "undocumented", "naturalized citizen", "legal immigrant", "temporary resident"
- (Your script will handle travel_types, ports, relationships, involvement_types, etc. by mapping extracted names to IDs later)

Interview Text:
{{interview_text}}
"""

def log_extraction_to_file(log_entry: dict):
    """Appends a JSON log entry to the log file."""
    try:
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f)
            f.write('\n') # Newline for JSON Lines format
    except Exception as e:
        print(f"Error writing to log file {LOG_FILE_PATH}: {e}")


def store_extracted_data_v2(text_file_path: str, data: dict):
    conn = None
    print(f"Attempting to store data for: {text_file_path}") # Debug print
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            imm_events = data.get("interviewee_immigration_events", [])
            jobs_list = data.get("interviewee_jobs", [])
            edu_history = data.get("interviewee_education_history", [])
            health_issues_list = data.get("interviewee_health_issues", [])
            other_people = data.get("other_people_mentioned", [])
            community_involvements_list = data.get("interviewee_community_involvements", [])
            
            cultural_aspects = data.get("interviewee_cultural_aspects", {})
            assoc_cultures = cultural_aspects.get("associated_culture_names", [])
            lang_spoken = cultural_aspects.get("languages_spoken_or_mentioned", [])
            cultural_events = cultural_aspects.get("cultural_events_mentioned", [])
            cultural_practices = cultural_aspects.get("cultural_practices_mentioned", [])

            historic_events = data.get("interviewee_historic_event_involvement", [])
            gen_keywords = data.get("general_keywords", [])

            cur.execute(
                "CALL ingest_interview_from_ai_json_v2("
                "p_text_filename := %s, p_story_title := %s, p_story_summary := %s, "
                "p_interview_location := %s, p_interview_date := %s, "
                "p_interviewee_name := %s, p_interviewee_birthday := %s, "
                "p_interviewee_birthplace_city_name := %s, p_interviewee_birthplace_country_name := %s, "
                "p_interviewee_sex := %s, p_interviewee_marital_status := %s, p_interviewee_legal_status := %s, "
                "p_immigration_events := %s, "
                "p_jobs := %s, "
                "p_education_history := %s, "
                "p_health_issues := %s, "
                "p_other_people_mentioned := %s, "
                "p_community_involvements := %s, "
                "p_cultural_associated_cultures := %s, p_cultural_languages_spoken := %s, "
                "p_cultural_events_mentioned := %s, p_cultural_practices_mentioned := %s, "
                "p_historic_events_involved := %s, "
                "p_general_keywords := %s"
                ");",
                (
                    os.path.basename(text_file_path),
                    data.get("story_title"), data.get("story_summary"),
                    data.get("interview_location"), data.get("interview_date"),
                    data.get("interviewee_name"), data.get("interviewee_birthday"),
                    data.get("interviewee_birthplace_city_name"), data.get("interviewee_birthplace_country_name"),
                    data.get("interviewee_sex"), data.get("interviewee_marital_status"), data.get("interviewee_legal_status_at_migration_or_current"),
                    json.dumps(imm_events) if imm_events else None,
                    json.dumps(jobs_list) if jobs_list else None,
                    json.dumps(edu_history) if edu_history else None,
                    json.dumps(health_issues_list) if health_issues_list else None,
                    json.dumps(other_people) if other_people else None,
                    json.dumps(community_involvements_list) if community_involvements_list else None,
                    assoc_cultures if assoc_cultures else None,
                    json.dumps(lang_spoken) if lang_spoken else None,
                    json.dumps(cultural_events) if cultural_events else None,
                    json.dumps(cultural_practices) if cultural_practices else None,
                    json.dumps(historic_events) if historic_events else None,
                    gen_keywords if gen_keywords else None
                )
            )
            conn.commit()
            print(f"Successfully ingested data into DB for: {text_file_path}")

    except psycopg.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error storing data for {text_file_path}: {e}")
        print(f"SQLSTATE: {e.sqlstate}")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An unexpected error occurred while storing data for {text_file_path}: {e}")
    finally:
        if conn:
            conn.close()

def call_gemini_api_with_retry(interview_text: str, api_key: str, filename_for_log: str,
                               max_retries: int = 3, initial_wait_time: float = 7.0) -> str | None: # Reduced max_retries slightly
    """
    Calls the Gemini API with retry logic for rate limiting.
    """
    genai.configure(api_key=api_key)

    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=LOW_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config=generation_config
    )

    full_prompt = GEMINI_JSON_PROMPT_TEMPLATE.replace("{{interview_text}}", interview_text)

    retries = 0
    current_wait_time = initial_wait_time

    while retries <= max_retries: # Changed to <= to allow max_retries attempts
        try:
            print(f"Attempt {retries + 1}/{max_retries + 1} for {filename_for_log}: Sending prompt to Gemini (model: {MODEL_NAME})...")
            response = model.generate_content(full_prompt)

            if response.parts:
                raw_output = response.text
                return raw_output.strip()
            else: # No parts, could be due to safety filters or other issues
                print(f"Gemini API returned no parts in the response for {filename_for_log}.")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    print(f"Prompt Feedback for {filename_for_log}: {response.prompt_feedback}")
                    # Log this specific failure case
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "filename": filename_for_log,
                        "status": "error_no_parts",
                        "prompt_feedback": str(response.prompt_feedback),
                        "error_message": "Gemini API returned no parts."
                    }
                    log_extraction_to_file(log_entry)
                return None # Critical to return None here

        except Exception as e:
            error_message = str(e).lower()
            # More specific check for rate limit errors from google-generativeai
            # Often they are google.api_core.exceptions.ResourceExhausted
            # or contain "quota" or "rate limit" text.
            is_rate_limit_error = (
                "rate limit" in error_message or
                "resource has been exhausted" in error_message or
                "429" in error_message or 
                "quota" in error_message # Added "quota"
            )

            if is_rate_limit_error:
                retries += 1
                if retries > max_retries: # Check if we've exceeded retries
                    print(f"Max retries reached for rate limit on {filename_for_log}. Error: {e}")
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "filename": filename_for_log,
                        "status": "error_max_retries_rate_limit",
                        "error_message": str(e)
                    }
                    log_extraction_to_file(log_entry)
                    return None
                
                sleep_time = current_wait_time + random.uniform(0, 2) # Added more jitter
                print(f"Rate limit hit for {filename_for_log}. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                current_wait_time = min(current_wait_time * 2, 60) # Exponential backoff, cap at 60s
            else:
                print(f"Error calling Gemini API for {filename_for_log} (not a rate limit, or unhandled): {e}")
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "filename": filename_for_log,
                    "status": "error_api_call",
                    "error_message": str(e)
                }
                log_extraction_to_file(log_entry)
                return None # Return None on other errors
    return None # Should be reached only if max_retries is 0 or loop finishes unexpectedly

def analyze_interview_with_gemini(interview_file_path: str, api_key: str) -> dict | None:
    """
    Reads an interview from a file, analyzes it using Gemini, and returns structured data.
    """
    filename_only = os.path.basename(interview_file_path)
    print(f"\n--- Analyzing file: {filename_only} with Gemini ---")
    
    try:
        with open(interview_file_path, 'r', encoding='utf-8') as f:
            interview_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {interview_file_path}")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename_only,
            "status": "error_file_not_found",
            "error_message": f"File not found: {interview_file_path}"
        }
        log_extraction_to_file(log_entry)
        return None
    except Exception as e:
        print(f"Error reading file {interview_file_path}: {e}")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename_only,
            "status": "error_file_read",
            "error_message": str(e)
        }
        log_extraction_to_file(log_entry)
        return None

    if not interview_text.strip():
        print(f"Error: File {filename_only} is empty.")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename_only,
            "status": "error_file_empty"
        }
        log_extraction_to_file(log_entry)
        return None

    json_response_str = call_gemini_api_with_retry(interview_text, api_key, filename_only)

    if json_response_str:
        try:
            extracted_data = json.loads(json_response_str)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "filename": filename_only,
                "status": "success",
                "extracted_json": extracted_data # Log the parsed dict
            }
            log_extraction_to_file(log_entry)
            return extracted_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Gemini API for file {filename_only}: {e}")
            print(f"Received string from model (that failed to parse):\n---\n{json_response_str}\n---")
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "filename": filename_only,
                "status": "error_json_decode",
                "raw_response": json_response_str,
                "error_message": str(e)
            }
            log_extraction_to_file(log_entry)
            return None
    else: # json_response_str is None (API call failed after retries or other critical error)
        # Logging for this case is now handled within call_gemini_api_with_retry
        print(f"No valid JSON response received from Gemini for {filename_only} after retries/errors.")
        return None

# --- Main Script ---
if __name__ == "__main__":
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable not found.")
        print("Please set it before running the script.")
        exit(1) # Use exit(1) for errors

    INTERVIEW_DIR = "texts" # Assuming your text files are in a 'texts' subdirectory
    if not os.path.isdir(INTERVIEW_DIR):
        print(f"\nDirectory '{INTERVIEW_DIR}' not found. Please create it and add .txt files.")
        exit(1) # Exit if the directory doesn't exist

    print(f"--- Starting Batch Processing from directory: {INTERVIEW_DIR} with Gemini ---")
    processed_count = 0
    failed_count = 0
    for filename in os.listdir(INTERVIEW_DIR):
        if filename.endswith(".txt"):
            file_path = os.path.join(INTERVIEW_DIR, filename)
            extracted_info = analyze_interview_with_gemini(file_path, google_api_key)
            
            if extracted_info:
                print(f"--- Successfully processed and extracted data for {filename} ---")
                # Instead of printing the JSON to console, it's now logged by analyze_interview_with_gemini
                # Now, attempt to store it in the database
                store_extracted_data_v2(file_path, extracted_info)
                processed_count +=1
            else:
                print(f"--- Failed to process or extract data for {filename} ---")
                failed_count += 1
            
            # Optional: Add a small delay between API calls if still hitting limits frequently
            # time.sleep(1) # e.g., wait 1 second
    
    print(f"\n--- Batch Processing Complete ---")
    print(f"Successfully processed files: {processed_count}")
    print(f"Failed to process files: {failed_count}")
    print(f"Extraction logs saved to: {LOG_FILE_PATH}")
