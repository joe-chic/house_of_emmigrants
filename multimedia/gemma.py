import json
import os
import torch
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# --- Configuration ---
# Adjust this to the exact Gemma model you have downloaded or want to use from Hugging Face Hub
# Examples: "google/gemma-2b-it", "google/gemma-7b-it", "google/gemma-1.1-2b-it"
MODEL_NAME = "google/gemma-3-1b-it" 

# Set to True to use 4-bit quantization with BitsAndBytes to save memory
# Requires bitsandbytes to be installed correctly
USE_QUANTIZATION = False

# Maximum number of new tokens the model can generate for the JSON output.
# Adjust if your JSON is often truncated or too long.
MAX_NEW_TOKENS = 1536 # Increased for potentially larger JSON outputs

# --- Prompt Definition (as provided by you) ---
GEMMA_PROMPT_TEMPLATE_REVISED = """
You will be given a block of text (an interview with a Swedish emigrant). Your task is to extract specific information and provide it as a single, valid JSON object. 
Do **not** output any extra text, comments, or explanation outside of the JSON object.

**Output Format Instructions:**
Produce a JSON object with the following keys. Ensure all string values are enclosed in double quotes. For empty fields, use an empty string "" or an empty array [] as appropriate.

- "story_title": (string) The title of the story or interview.
- "story_description": (string) A brief description or summary of the interview.
- "first_name_interviewed": (string) The first name of the person being interviewed.
- "first_surname_interviewed": (string) The first surname of the person being interviewed.
- "fullname_others": (array of strings) Full names of other people mentioned significantly in the interview. Example: ["Karl Andersson", "Maria Lundgren"].
- "sex_interviewed": (string) Must be one of: "female", "male".
- "marital_status_interviewed": (string) The marital status of the interviewee. Must be one of the valid values listed below.
- "education_level_interviewed": (string) The education level of the interviewee. Must be one of the valid values listed below.
- "occupation_interviewed": (string) The occupation(s) of the interviewee.
- "religion_interviewed": (string) The religion of the interviewee, if mentioned.
- "legal_status_interviewed": (string) The legal status of the interviewee at the time of migration. Must be one of the valid values listed below.
- "departure_date": (string) The date or approximate time of departure (e.g., "1903-05-15", "Spring 1903", "1903").
- "destination_country": (string) The country the interviewee emigrated to.
- "motive_migration": (string) The main reason for migration. Must be one of the valid values listed below.
- "travel_method": (array of strings) Methods of travel used. Each element must be one of the valid values listed below. Example: ["train", "steamship"].
- "return_plans": (string) Any mention of plans or desires to return.
- "important_keywords": (array of strings) 5-10 most salient keywords or phrases from the interview.

**Valid Values for Specific Fields (match exactly):**

- **sex_interviewed**: "female", "male"
- **travel_method**: "steamship", "sailboat", "train", "horse-drawn carriage", "on foot", "wagon or cart", "automobile"
- **marital_status_interviewed**: "single", "married", "widowed", "divorced", "separated", "engaged"
- **education_level_interviewed**: "no formal education", "primary school", "some secondary school", "completed secondary school", "trade or vocational training", "some college/university", "completed college/university", "illiterate"
- **legal_status_interviewed**: "citizen of origin country", "stateless", "refugee", "asylum seeker", "undocumented", "naturalized citizen", "legal immigrant", "temporary resident"
- **motive_migration**: "economic opportunity", "family reunification", "religious persecution", "political persecution", "war/conflict", "famine or natural disaster", "education", "adventure", "land ownership", "forced migration"

**Your goal is to populate these fields with actual information extracted from the interview text below.** Output only the single, valid JSON object.

—BEGIN INTERVIEW TEXT—
{{interview_text}}
—END INTERVIEW TEXT—
"""

def load_model_and_tokenizer(model_name: str, use_quantization: bool):
    """Loads the Gemma model and tokenizer."""
    print(f"Loading model: {model_name}...")
    
    quantization_config = None
    if use_quantization:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 # or torch.float16
        )
        print("Using 4-bit quantization.")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",  # Automatically selects GPU if available, else CPU
            torch_dtype=torch.bfloat16 if quantization_config else torch.float32 # Use bfloat16 with quantization
        )
        print("Model and tokenizer loaded successfully.")
        return model, tokenizer
    except Exception as e:
        print(f"Error loading model/tokenizer: {e}")
        print("Please ensure you have a working internet connection for the first download,")
        print(f"that the model name '{model_name}' is correct, and you have enough RAM/VRAM.")
        print("If using quantization, ensure 'bitsandbytes' is installed correctly.")
        return None, None

def call_gemma_local(interview_text: str, model, tokenizer, device, interview_file_name: str) -> str | None:
    # Construct the part of the prompt that comes AFTER the interview text
    # This emphasizes that the JSON generation task is the very next step.
    final_instruction = "\n\nNow, provide the single, valid JSON object based on the text above:"

    full_prompt_parts = [
        GEMMA_PROMPT_TEMPLATE_REVISED.replace("{{interview_text}}", interview_text),
        final_instruction
    ]
    full_prompt = "".join(full_prompt_parts)

    # --- Tokenizer and Length Check ---
    # It's better to tokenize only once before sending to model.
    # Calculate tokens for the prompt instructions part first
    prompt_instructions_only = GEMMA_PROMPT_TEMPLATE_REVISED.replace("{{interview_text}}", "") + final_instruction
    inputs_instructions = tokenizer(prompt_instructions_only, return_tensors="pt")
    instruction_tokens = inputs_instructions['input_ids'].shape[1]

    # Calculate tokens for the interview text
    inputs_interview = tokenizer(interview_text, return_tensors="pt")
    interview_tokens = inputs_interview['input_ids'].shape[1]

    total_estimated_tokens = instruction_tokens + interview_tokens
    # Gemma's context is often 8192, but let's be a bit conservative for output space
    # tokenizer.model_max_length might give you the model's theoretical max
    model_max_context = getattr(tokenizer, 'model_max_length', 8192)
    print(f"[{interview_file_name}] Estimated instruction tokens: {instruction_tokens}")
    print(f"[{interview_file_name}] Estimated interview tokens: {interview_tokens}")
    print(f"[{interview_file_name}] Total estimated input tokens: {total_estimated_tokens}")
    print(f"[{interview_file_name}] Model max context: {model_max_context}")

    # Reserve space for output, e.g., MAX_NEW_TOKENS
    if total_estimated_tokens + MAX_NEW_TOKENS > model_max_context:
        print(f"WARNING: [{interview_file_name}] Estimated total tokens ({total_estimated_tokens} input + {MAX_NEW_TOKENS} output) may exceed model's max context ({model_max_context}). Attempting to proceed, but output may be truncated or incorrect.")
        # Simplistic truncation of interview_text if too long. This is a basic approach.
        # A more sophisticated approach would summarize or chunk.
        allowable_interview_tokens = model_max_context - instruction_tokens - MAX_NEW_TOKENS - 50 # 50 for safety margin
        if allowable_interview_tokens < interview_tokens and allowable_interview_tokens > 0:
            print(f"[{interview_file_name}] Truncating interview text from {interview_tokens} to approx {allowable_interview_tokens} tokens.")
            # This is a rough truncation. Tokenizing, slicing token IDs, then decoding is more precise.
            # For simplicity here, we'll just use a character-based approximation or skip for now.
            # A better way:
            interview_token_ids = inputs_interview['input_ids'][0][:allowable_interview_tokens]
            truncated_interview_text = tokenizer.decode(interview_token_ids, skip_special_tokens=True)
            print(f"[{interview_file_name}] Original interview length (chars): {len(interview_text)}, Truncated (chars): {len(truncated_interview_text)}")
            interview_text = truncated_interview_text # Use truncated text
            full_prompt = GEMMA_PROMPT_TEMPLATE_REVISED.replace("{{interview_text}}", interview_text) + final_instruction
        elif allowable_interview_tokens <= 0:
            print(f"ERROR: [{interview_file_name}] Not enough space in context window even for truncated text. Skipping this file.")
            return None


    inputs = tokenizer(full_prompt, return_tensors="pt", return_attention_mask=True).to(device)
    actual_input_tokens = inputs['input_ids'].shape[1]
    print(f"[{interview_file_name}] Actual tokens being sent to model: {actual_input_tokens}")
    if actual_input_tokens + MAX_NEW_TOKENS > model_max_context:
         print(f"WARNING: [{interview_file_name}] AFTER TRUNCATION OR NO TRUNCATION: Actual input tokens ({actual_input_tokens}) + output tokens ({MAX_NEW_TOKENS}) may still exceed model's max context ({model_max_context}).")


    print(f"[{interview_file_name}] Generating response...")
    try:
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.2,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id
        )

        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract JSON (using the improved extraction from previous suggestion)
        json_string = None
        match_markdown = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", response_text, re.DOTALL) # Use [\s\S] for multiline
        if match_markdown:
            json_string = match_markdown.group(1)
        else:
            json_start_index = response_text.find('{')
            json_end_index = response_text.rfind('}')
            if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                json_string = response_text[json_start_index : json_end_index + 1]
            else:
                print(f"[{interview_file_name}] Could not find JSON object delimiters '{{' and '}}' in the model's response.")
                print(f"[{interview_file_name}] Full response was:\n{response_text}")
                return None

        json_string = json_string.strip()

        if not json_string: # If json_string is empty after strip
            print(f"[{interview_file_name}] Extracted JSON string is empty.")
            print(f"[{interview_file_name}] Full response was:\n{response_text}")
            return None

        # Heuristic check for schema template (optional, but can be helpful)
        if (('": string,' in json_string or '": "female" | "male",' in json_string) and len(json_string) < 500) or full_prompt.strip().endswith(json_string): # check if it just echoed prompt
            print(f"[{interview_file_name}] Model likely returned the schema template or echoed prompt instead of filled JSON.")
            print(f"[{interview_file_name}] Problematic JSON string received:\n---\n{json_string}\n---")
            return None

        return json_string

    except Exception as e:
        print(f"[{interview_file_name}] Error during model generation or JSON extraction: {e}")
        # For debugging, you might want to see the response_text even if an error occurs later
        # if 'response_text' in locals():
        #    print(f"[{interview_file_name}] Response text at time of error:\n{response_text}")
        return None

def analyze_interview_file(file_path: str, model, tokenizer, device, filename) -> dict | None:
    """
    Reads an interview from a file, analyzes it, and returns structured data.
    """
    print(f"\n--- Analyzing file: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            interview_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

    if not interview_text.strip():
        print("Error: File is empty.")
        return None
        
    json_response_str = call_gemma_local(interview_text, model, tokenizer, device, filename)
    
    if json_response_str:
        try:
            extracted_data = json.loads(json_response_str)
            return extracted_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from AI model for file {file_path}: {e}")
            print(f"Received string from model:\n---\n{json_response_str}\n---")
            return None
    return None

# --- Main Script ---
if __name__ == "__main__":
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME, USE_QUANTIZATION)

    if model and tokenizer:
        device = model.device # Get the device the model was loaded onto
        print(f"Model is on device: {device}")


        # --- Process all .txt files in a directory ---
        # Create a directory named 'text' in the same location as the script
        # and place your .txt interview files there.
        interview_dir = "text" 
        if not os.path.exists(interview_dir):
            print(f"\nDirectory '{interview_dir}' not found. Please create it and add .txt files to process multiple files.")
        else:
            print(f"\n--- Processing files in directory: {interview_dir} ---")
            for filename in os.listdir(interview_dir):
                if filename.endswith(".txt"):
                    file_path = os.path.join(interview_dir, filename)
                    extracted_info = analyze_interview_file(file_path, model, tokenizer, device, filename)
                    if extracted_info:
                        print(f"\n--- Extracted Information for {filename} ---")
                        for key, value in extracted_info.items():
                            print(f"  \"{key}\": {repr(value)}")
                        # Here, you would typically save this 'extracted_info' to your database
                        # or a structured file (e.g., a larger JSON file, CSV).
                        print(f"--- Successfully processed {filename} ---")
                    else:
                        print(f"--- Failed to process {filename} ---")
    else:
        print("Exiting due to model loading failure.")
