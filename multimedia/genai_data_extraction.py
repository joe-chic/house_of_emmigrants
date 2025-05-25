import json
import os
import re
import google.generativeai as genai

# --- Configuration ---
MODEL_NAME = "gemini-2.0-flash-lite" 
LOW_TEMPERATURE = 0.1 # For more deterministic output
MAX_OUTPUT_TOKENS = 2048 # Max tokens Gemini will generate for the JSON. Adjust if needed.

# --- Prompt Definition ---
# This prompt is designed to guide Gemini when using its JSON mode.
# The model will be forced to output JSON, so the description of fields is key.
GEMINI_JSON_PROMPT_TEMPLATE = """
You are an expert data extractor. Based on the following interview text with a Swedish emigrant, extract the specified information and structure it as a single, valid JSON object.

The JSON object must conform to the following structure and field descriptions:

- "story_title": (string) A concise title for the story or interview.
- "story_description": (string) A brief 1-2 sentence summary of the interview's main topics.
- "first_name_interviewed": (string) The first name of the primary person interviewed.
- "first_surname_interviewed": (string) The first surname of the primary person interviewed.
- "fullname_others": (array of strings) Full names (e.g., "FirstName LastName") of other individuals significantly mentioned. If no other names, use an empty array [].
- "sex_interviewed": (string) The sex of the primary interviewee. Must be one of: "female", "male", or an empty string if not specified.
- "marital_status_interviewed": (string) Marital status of the interviewee. Must be one of: "single", "married", "widowed", "divorced", "separated", "engaged", or an empty string if not specified.
- "education_level_interviewed": (string) Education level. Must be one of: "no formal education", "primary school", "some secondary school", "completed secondary school", "trade or vocational training", "some college/university", "completed college/university", "illiterate", or an empty string if not specified.
- "occupation_interviewed": (string) Occupation(s) of the interviewee.
- "religion_interviewed": (string) Religion of the interviewee, if mentioned.
- "legal_status_interviewed": (string) Legal status at migration. Must be one of: "citizen of origin country", "stateless", "refugee", "asylum seeker", "undocumented", "naturalized citizen", "legal immigrant", "temporary resident", or an empty string if not specified.
- "departure_date": (string) Date/approximate time of departure (e.g., "1903-05-15", "Spring 1903", "1903").
- "destination_country": (string) The primary country the interviewee emigrated to.
- "motive_migration": (string) Main reason for migration. Must be one of: "economic opportunity", "family reunification", "religious persecution", "political persecution", "war/conflict", "famine or natural disaster", "education", "adventure", "land ownership", "forced migration", or an empty string if not specified.
- "travel_method": (array of strings) Travel methods used. Each must be one of: "steamship", "sailboat", "train", "horse-drawn carriage", "on foot", "wagon or cart", "automobile". If none specified or multiple, use an array.
- "return_plans": (string) Any mention of plans/desires to return.
- "important_keywords": (array of strings) 5-10 most salient keywords or phrases capturing the core topics.

Use an empty string "" for string fields or an empty array [] for array fields if the information is not found in the text.

Interview Text:
{{interview_text}}
"""

def call_gemini_api(interview_text: str, api_key: str) -> str | None:
    """
    Calls the Gemini API to extract information from the interview text
    and attempts to get a structured JSON output.
    """
    try:
        genai.configure(api_key=api_key)

        generation_config = genai.types.GenerationConfig(
            # This forces the model to output JSON.
            response_mime_type="application/json",
            temperature=LOW_TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS
        )

        model = genai.GenerativeModel(
            MODEL_NAME,
            generation_config=generation_config,
        )

        full_prompt = GEMINI_JSON_PROMPT_TEMPLATE.replace("{{interview_text}}", interview_text)

        print(f"Sending prompt to Gemini (model: {MODEL_NAME})...")
        # print(f"--- Prompt Start ---\n{full_prompt[:500]}...\n--- Prompt End ---") # For debugging prompt

        response = model.generate_content(full_prompt)

        # When response_mime_type="application/json", the model output should be directly parseable.
        # The response.text should contain the JSON string.
        if response.parts:
            json_string = response.text # .text directly gives the string content
            # print(f"--- Raw JSON String from Gemini ---\n{json_string}\n--- End Raw JSON ---") # For debugging
            return json_string.strip()

        print("Gemini API returned no parts in the response.")
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            print(f"Prompt Feedback: {response.prompt_feedback}")
        return None

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # You might want to check for specific error types, e.g., related to API key, quota, content filtering
        # if "API key not valid" in str(e):
        #    print("Please check your GOOGLE_API_KEY environment variable or the key itself.")
        # if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'): 
        # For some google.api_core.exceptions
        #    print(f"Prompt Feedback: {e.response.prompt_feedback}")

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

    json_response_str = call_gemini_api(interview_text, api_key)

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
