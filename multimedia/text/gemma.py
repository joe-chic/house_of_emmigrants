import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# --- Configuration ---
# Adjust this to the exact Gemma model you have downloaded or want to use from Hugging Face Hub
# Examples: "google/gemma-2b-it", "google/gemma-7b-it", "google/gemma-1.1-2b-it"
MODEL_NAME = "google/gemma-2b-it" 

# Set to True to use 4-bit quantization with BitsAndBytes to save memory
# Requires bitsandbytes to be installed correctly
USE_QUANTIZATION = True 

# Maximum number of new tokens the model can generate for the JSON output.
# Adjust if your JSON is often truncated or too long.
MAX_NEW_TOKENS = 1536 # Increased for potentially larger JSON outputs

# --- Prompt Definition (as provided by you) ---
GEMMA_PROMPT_TEMPLATE = """
You will be given a block of text (an interview with a Swedish emigrant). Extract exactly the fields listed below and output **only** a single, valid JSON object. Do **not** output any extra text, keys, or explanation.

Required JSON schema:
{
  "story_title": string,
  "story_description": string,
  "first_name_interviewed": string,
  "first_surname_interviewed": string,
  "fullname_others": string[],
  "sex_interviewed": "female" | "male",
  "marital_status_interviewed": string,
  "education_level_interviewed": string,
  "occupation_interviewed": string,
  "religion_interviewed": string,
  "legal_status_interviewed": string,
  "departure_date": string,        // e.g., "1903-05-15", "Spring 1903", "1903"
  "destination_country": string,
  "motive_migration": string,
  "travel_method": string[],
  "return_plans": string,
  "important_keywords": string[]   // Array of the most salient keywords from the interview
}

**Valid values (must match exactly)**

- **sex_interviewed**
  `female`
  `male`

- **travel_method**
  `steamship`
  `sailboat`
  `train`
  `horse-drawn carriage`
  `on foot`
  `wagon or cart`
  `automobile`

- **marital_status_interviewed**
  `single`
  `married`
  `widowed`
  `divorced`
  `separated`
  `engaged`

- **education_level_interviewed**
  `no formal education`
  `primary school`
  `some secondary school`
  `completed secondary school`
  `trade or vocational training`
  `some college/university`
  `completed college/university`
  `illiterate`

- **legal_status_interviewed**
  `citizen of origin country`
  `stateless`
  `refugee`
  `asylum seeker`
  `undocumented`
  `naturalized citizen`
  `legal immigrant`
  `temporary resident`

- **motive_migration**
  `economic opportunity`
  `family reunification`
  `religious persecution`
  `political persecution`
  `war/conflict`
  `famine or natural disaster`
  `education`
  `adventure`
  `land ownership`
  `forced migration`

**Instructions:**
1. Read the input text.
2. Populate each field exactly as per the schema.
3. If a field is missing, write empty string "" or null for non-string fields where appropriate, or an empty array [] for array fields. For string fields, use an empty string if not found.
4. **important_keywords:** list the top 5–10 terms or phrases that capture the core topics of the interview.
5. Output exactly one valid JSON object—no comments, no extra keys, no surrounding prose.

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

def call_gemma_local(interview_text: str, model, tokenizer, device) -> str | None:
    """
    Calls the local Gemma model to extract information.
    Returns the JSON string or None if an error occurs.
    """
    full_prompt = GEMMA_PROMPT_TEMPLATE.replace("{{interview_text}}", interview_text)

    # Gemma uses specific chat tokens if it's an instruction-tuned model.
    # For raw text completion with this kind of structured prompt, direct input is often fine.
    # If you get poor results, you might need to wrap the prompt in chat template tokens:
    # messages = [{"role": "user", "content": full_prompt}]
    # prompt_for_model = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # inputs = tokenizer(prompt_for_model, return_tensors="pt").to(device)
    
    inputs = tokenizer(full_prompt, return_tensors="pt", return_attention_mask=True).to(device)

    print(f"Generating response (input length: {inputs['input_ids'].shape[1]})...")
    try:
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True, # Recommended for instruction following to allow some flexibility
            temperature=0.3, # Lower temperature for more deterministic, factual output
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id # Important for stopping generation
        )
        
        # Decode the generated tokens
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # The prompt asks the model to ONLY output JSON.
        # We need to extract the JSON part from the response.
        # The model might sometimes include the prompt in its output or other text.
        
        # Simplistic extraction: find the first '{' and last '}'
        # A more robust method might be needed if the model isn't strict.
        json_start_index = response_text.find('{')
        json_end_index = response_text.rfind('}')
        
        if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
            json_string = response_text[json_start_index : json_end_index + 1]
            return json_string.strip()
        else:
            print("Could not find JSON object in the model's response.")
            print("Full response was:\n", response_text)
            return None

    except Exception as e:
        print(f"Error during model generation: {e}")
        return None

def analyze_interview_file(file_path: str, model, tokenizer, device) -> dict | None:
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
        
    json_response_str = call_gemma_local(interview_text, model, tokenizer, device)
    
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

        # --- OPTION 1: Process a single sample interview text ---
        sample_interview_text = """
        Interviewer: Welcome, Anders. Can you state your full name for our records?
        Anders: Anders Persson.
        Interviewer: When did you leave Sweden, Mr. Persson?
        Anders: It was late summer, August of 1888. I was just a young man, single at the time.
        Interviewer: And your reasons for emigrating?
        Anders: Land was scarce back home, and America promised economic opportunity. My cousin, Lars, had gone a few years prior and wrote of good wages.
        Interviewer: How did you travel?
        Anders: A long trip! First a small boat to connect to a train, and then the big steamship from Gothenburg. It took many weeks.
        Interviewer: What was your education and occupation?
        Anders: I had basic primary school. I worked as a farm laborer in Sweden. My legal status was simply a citizen of Sweden.
        Interviewer: Did you have any plans to return to Sweden?
        Anders: At the time, I thought perhaps one day, but America became my home.
        Interviewer: Thank you, Anders. This is very helpful. The journey itself, you mentioned steamship and train. Any other means?
        Anders: No, mainly those two. The steamship was the major part. We were Lutherans, our family.
        """
        
        print("\n--- Analyzing sample interview text ---")
        # For single text, directly call call_gemma_local and parse
        json_str_sample = call_gemma_local(sample_interview_text, model, tokenizer, device)
        if json_str_sample:
            try:
                extracted_info_sample = json.loads(json_str_sample)
                print("\n--- Extracted Information (Sample Text) ---")
                for key, value in extracted_info_sample.items():
                    print(f"  \"{key}\": {repr(value)}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from sample text analysis: {e}")
                print(f"Received string: {json_str_sample}")
        else:
            print("Failed to get JSON response for sample text.")


        # --- OPTION 2: Process all .txt files in a directory ---
        # Create a directory named 'interviews' in the same location as the script
        # and place your .txt interview files there.
        interview_dir = "interviews" 
        if not os.path.exists(interview_dir):
            print(f"\nDirectory '{interview_dir}' not found. Please create it and add .txt files to process multiple files.")
        else:
            print(f"\n--- Processing files in directory: {interview_dir} ---")
            for filename in os.listdir(interview_dir):
                if filename.endswith(".txt"):
                    file_path = os.path.join(interview_dir, filename)
                    extracted_info = analyze_interview_file(file_path, model, tokenizer, device)
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
