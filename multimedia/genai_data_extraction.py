import json
import os
import re
import google.generativeai as genai

# --- Configuration ---
MODEL_NAME = "gemini-2.0-flash"
LOW_TEMPERATURE = 0.1
MAX_OUTPUT_TOKENS = 4096

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
      // Potentially add more fields here if you want to capture their sex, birthdate etc. if mentioned.
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

def call_gemini_api_with_retry(interview_text: str, api_key: str,
                               max_retries: int = 5, initial_wait_time: float = 5.0) -> str | None:
    """
    Calls the Gemini API with retry logic for rate limiting.
    """
    genai.configure(api_key=api_key) # Configure once if not done globally

    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=LOW_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

    # Use the MODEL_NAME from your successful script
    model = genai.GenerativeModel(
        MODEL_NAME, # Ensure this is the model that gave good results
        generation_config=generation_config
    )

    full_prompt = GEMINI_JSON_PROMPT_TEMPLATE.replace("{{interview_text}}", interview_text)

    retries = 0
    current_wait_time = initial_wait_time

    while retries < max_retries:
        try:
            print(f"Attempt {retries + 1}/{max_retries}: Sending prompt to Gemini (model: {MODEL_NAME})...")
            response = model.generate_content(full_prompt)

            if response.parts:
                raw_output = response.text
                return raw_output.strip()

            print("Gemini API returned no parts in the response.")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                print(f"Prompt Feedback: {response.prompt_feedback}")
            return None # Or handle as an error

        except Exception as e: # Catching a broad exception; more specific is better
            error_message = str(e).lower()
            if "rate limit" in error_message or "resource has been exhausted" in error_message or "429" in error_message:
                retries += 1
                if retries >= max_retries:
                    print(f"Max retries reached for rate limit. Error: {e}")
                    return None

                # Exponential backoff with jitter
                sleep_time = current_wait_time + random.uniform(0, 1)
                print(f"Rate limit hit. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                current_wait_time *= 2 # Exponential backoff
            else:
                # Not a rate limit error, or a different kind of error
                print(f"Error calling Gemini API (not a rate limit, or unhandled): {e}")
                return None
    return None

def analyze_interview_with_gemini(interview_file_path: str, api_key: str) -> dict | None:
    """
    Reads an interview from a file, analyzes it using Gemini, and returns structured data.
    """
    print(f"\n--- Analyzing file: {os.path.basename(interview_file_path)} with Gemini ---")
    try:
        with open(interview_file_path, 'r', encoding='utf-8') as f:
            interview_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {interview_file_path}")
        return None
    except Exception as e:
        print(f"Error reading file {interview_file_path}: {e}")
        return None

    if not interview_text.strip():
        print("Error: File is empty.")
        return None

    # Rudimentary check for very long texts - Gemini has large context windows (e.g., 1M for 1.5 Pro)
    # but free tiers or Flash might have practical limits for single requests, or processing cost.
    # For Gemini, the token limit is usually on (input + output).
    # The SDK/API will error out if the prompt is too long.
    # print(f"Interview text length (chars): {len(interview_text)}")

    json_response_str = call_gemini_api_with_retry(interview_text, api_key)

    if json_response_str:
        try:
            # The API in JSON mode should directly return a parsable JSON string
            extracted_data = json.loads(json_response_str)
            return extracted_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Gemini API for file {os.path.basename(interview_file_path)}: {e}")
            print(f"Received string from model (that failed to parse):\n---\n{json_response_str}\n---")
            return None
    return None

# --- Main Script ---
if __name__ == "__main__":
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable not found.")
        print("Please set it before running the script.")
        exit()

    INTERVIEW_DIR = "texts"
    if not os.path.exists(INTERVIEW_DIR):
        print(f"\nDirectory '{INTERVIEW_DIR}' not found. Skipping batch processing.")
    else:
        print(f"\n--- Processing files in directory: {INTERVIEW_DIR} with Gemini ---")
        for filename in os.listdir(INTERVIEW_DIR):
            if filename.endswith(".txt"):
                file_path = os.path.join(INTERVIEW_DIR, filename)
                extracted_info = analyze_interview_with_gemini(file_path, google_api_key)
                if extracted_info:
                    print(f"\n--- Extracted Information for {filename} (Gemini) ---")
                    print(json.dumps(extracted_info, indent=2))
                    print(f"--- Successfully processed {filename} with Gemini ---")
                else:
                    print(f"--- Failed to process {filename} with Gemini ---")
