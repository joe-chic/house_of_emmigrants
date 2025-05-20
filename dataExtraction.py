import os
import regex as re
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# ... (Keep DB_CONFIG and all REGEX_* constants as they were) ...
# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "house_of_emigrants",
    "user": "postgres",
    "password": "666",
    "host": "localhost",
    "port": "5432"
}

# --- Regex Patterns (Ensure these are comprehensive and correct) ---
# Using the previously defined REGEX_* constants
REGEX_NAMES = r"\b(Conrad Reinell|Annie Erickson|Jack Pennies|Mary Livingston|Leo Bing|Peter|Rich Snell Hall|Joan Crawford|Franchot Tone|Mr\. Tone|Will Rogers|Hal Moore|Evelyn Venable|Ed Garner|Axel|Ellen|Bill Warner|Dr\. Hickman|Dr\. Rieger|Florence Gustafsson|Ole Larsen|Ransom|Selma|Lex parent|Rammelisa Jansson|Elin Adele|Carl|Owen|Harold|Walter|Franz Gabrielson|Colonel Gabrielson|Miriam|Carl Anderson|Eleonora Anderson|Britta Matilda Elizabeth Olin|Gustav Vasa|Harlandqvist|Johan Andersson|Patrician Val|Ericsson|Martin|Gunnar|Nordem Highland|Adolf de Kael|Marta|Daniel|Ed Tate|Ruby Hall|Clara Lawson|Roy|Mr\. Rush|Pastor Reina Kron|Pastor Bergström|Pastor Westerberg|Rachel Sward|Pastor Ehrling|Pastor Holt|Pastor Andersson|Richard Pearson|Russell Pearson|Stephanie|Zage|Pastor Palm|Bill|Gus|Fritidsbeteget|Utvandlingsbeteget|Drottningholm|Kungsholm|Viva)\b|\b(?:(?:Mr|Mrs|Miss|Ms|Dr|Pastor|Colonel)\.?\s+)?([A-Z][a-z]+(?:(?:\s+|-)[A-Z][a-z]+){0,2})\b"
REGEX_LOCATIONS = r"\b(Minneapolis|Iowa|Göteborg|New York|United States|Ellis Island|Chicago|Carolina|Canada|Washington|State of Washington|Buffalo|Pontiac|Detroit|Duluth|River Island|Minnesota|Wisconsin|Superior|South Superior|Illinois|Galesburg|Knoxville|Henderson County|Big River Yard|Jameson|California|New York City|Beverly Hills|Long Beach|Jamestown|Pennsylvania|Warwick|Rhode Island|Port Talcott|Providence|Salt Lake City|Hollywood|Hollywood and Vine|Brentwood Heights|England|Europe|Florida|Molin|Amerika|Lin|Lynn|Massachusetts|Owatana|Albert Lee|New Windsor|Michigan|Leamington|Ohio|LA|Winnebago|Rödön|Jämtland|Östersund|Storskön|University of Manitoba|China|Finland|Vasa|Sweden|Gulf of Bosnia|Aspås|Trondheim|Norway|Winnipeg|Klockarnäs|Nygården|Falu|Stockholm|Eriksdale|Minnadosa|Quigley Drive|Klerken|Belgium|East Flanders|West Flanders|Fourth Avenue|14th Street|East Moline|France|Davenport|Third street|Silvis|Holy Trinity|Västlanda|Westland Lutheran church|Bertranda|Adulhamn|Holdridge|Swede Bay|Binksburg|Waterbury|Bunker Hill Congregational Church|New Britain|Connecticut|Los Angeles|San Francisco|New England|Cranston|Olien|Rochester|Nebraska|Swedhåne|Malmö|Sturmsburg|Swedland|Tucson|Arizona|Norwalk|Webster|Läkontariot|Portville|Park Ridge|Schomburg|Kewani|Rockford|Decatur|Malin)\b|\b([A-Z][a-z]+(?:(?:\s+[A-Z][a-z]+){0,2})(?:\s+(?:County|State|Island|Yard|City|Bay|Mountains|Street|Avenue|Heights|Drive))?)\b"
REGEX_DATES_TIMES = r"(?i)\b(?:(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+the\s+\d{1,2}(?:st|nd|rd|th)?)|(?:\d{1,2}(?:st|nd|rd|th)?\s+of\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december))|(?:(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{1,2},?\s+\d{4})|(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december),?\s+\d{4}))|(?:\d{1,2}\.\s*(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4})|(?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})|(?:(?:19|20)\d{2}s)|(?:(?:the\s+)?\d{2}s)|(?:(?:first|last|next)\s+(?:day|week|month|year|morning|night))|(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s+(?:morning|afternoon|evening|night))?)|(?:morning|afternoon|evening|night|tonight|today|yesterday|tomorrow)|(?:(?:midnight|noon))|(?:(?:\d{1,2}(?:[:.]\d{2})?)\s*o'clock)|(?:year\s+2000)|(?:(?:(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|hundreds)\s+(?:year|month|week|day|hour|minute)s?)|(?:year\s+and\s+a\s+half)|(?:month\s+or\s+two)|(?:ten\s+days)))\b"
REGEX_KEYWORDS = r"(?i)\b(hello|yes|yeah|ja|no|cancelled|urgent)\b"
REGEX_SEX_TEXT = r"(?i)\b(male|female|man|woman|boy|girl)\b"
REGEX_AGE = r"\b(?:(\d{1,3})\s*years\s*old|age\s*of\s*(\d{1,3})|age\s*(\d{1,3})|was\s*(\d{1,3})(?:\s+years)?\b)\b|(?<=year\s*old\s*when\s*I\s*(?:was|came)\s*)\b(\d{1,2})\b"
REGEX_MARITAL_STATUS_TEXT = r"(?i)\b(single|married|divorced|separated|widow(?:ed)?|engaged)\b"
REGEX_EDUCATION_TEXT = r"(?i)\b(grade\s*school|high\s*school|evening\s*school|business\s*course|college(?:\s*school)?|university|educated|learned\s*to|studied|degree\s*(?:in\s*\w+)?|diploma|did\s*not\s*finish\s*(?:high\s*)?school|went\s*to\s*school\s*(?:in|at)?|took\s*grades\s*\w+\s*to\s*\w+)\b"
REGEX_OCCUPATION_TEXT = r"(?i)\b(?:worked\s*(?:as\s*a|in\s*a|for)?|job\s*(?:was|is)|occupation\s*(?:is|was)|I\s*(?:am|was)\s*a(?:n)?|my\s*profession\s*(?:is|was)|profession\s*of)\s*([a-zA-Z\s\-]+(?:(?:\s*|-)(?:man|woman|worker|operator|maker|keeper|master|hand|laborer|smith|wright|monger|ster))?)\b|\b(pastor|minister|priest|rabbi|imam|doctor|surgeon|physician|nurse|teacher|professor|educator|engineer|architect|designer|developer|programmer|analyst|scientist|researcher|lawyer|attorney|judge|paralegal|accountant|auditor|consultant|manager|director|supervisor|foreman|executive|administrator|clerk|secretary|assistant|receptionist|writer|author|editor|journalist|reporter|artist|musician|actor|performer|dancer|designer|photographer|farmer|rancher|gardener|forester|fisherman|hunter|chef|cook|baker|waiter|waitress|bartender|hostess|carpenter|plumber|electrician|mechanic|technician|operator|machinist|welder|builder|constructor|laborer|driver|pilot|captain|sailor|merchant|vendor|salesman|saleswoman|retailer|shopkeeper|cashier|librarian|curator|archivist|police\s*officer|firefighter|soldier|military|officer|guard|janitor|custodian|cleaner|housekeeper|maid|nanny|caregiver|volunteer|student|apprentice|intern|retired|unemployed|homemaker|housewife|soccer-stien|conductor|tool\s*and\s*die\s*maker|lathe\s*operator|molder|aviator|car\s*salesman)\b"
REGEX_RELIGION_TEXT = r"(?i)\b(Lutheran|Catholic|Jewish|Protestant|Baptist|Methodist|Presbyterian|Episcopalian|Evangelical|Pentecostal|Mormon|Latter-day\s*Saints|Jehovah's\s*Witness|Seventh-day\s*Adventist|Adventist|Quaker|Mennonite|Amish|Christian|Islam|Muslim|Hindu|Buddhist|Sikh|Bahá'í|Atheist|Agnostic|Covenant\s*Church|Mission\s*Church|Congregational\s*Church|Salvation\s*Army)\b"
REGEX_LEGAL_STATUS_TEXT = r"(?i)\b(citizen|immigrant|emigrant|migrant|refugee|asylum\s*seeker|visa\s*(?:holder)?|green\s*card|permanent\s*resident|naturalized|alien|non-resident|undocumented|papers|Fritidsbeteget|Utvandlingsbeteget|civiliseringar|quota)\b"
REGEX_MOTIVE_MIGRATION = r"(?i)\b(?:motive\s*(?:for|was)|reason\s*(?:for|was)|came\s*(?:for|because|to)|left\s*(?:for|because|to)|migrated\s*(?:for|because|to)|moved\s*(?:for|because|to)|seeking|in\s*search\s*of|escape\s*(?:from)?|due\s*to|opportunity|better\s*life|economic\s*reasons|political\s*reasons|religious\s*reasons|reunite\s*with\s*family|join\s*family|employment|work|job|hard\s*times|no\s*work|famine|war|persecution|adventure|studies|education|health\s*reasons|climate|land|gold\s*rush|quota\s*(?:was\s*opened)?)\b(?:[^.,;]*(?:work|job|opportunities|family|freedom|war|famine|persecution|better\s*life|economic\s*conditions|studies|health)[^.,;]*)?"
REGEX_TRAVEL_METHOD_TEXT = r"(?i)\b(ship|steamer|boat|vessel|ferry|liner|sailed\s*on|went\s*on|train|railroad|railway|by\s*rail|car|automobile|bus|coach|airplane|aeroplane|by\s*air|flew\s*on|walked|on\s*foot|horseback|wagon|cart|Drottningholm|Kungsholm|Stockholm|Viva)\b"
REGEX_RETURN_PLANS = r"(?i)\b(?:plan(?:s|ned)?\s*(?:to\s*return|to\s*go\s*back)|intend(?:s|ed)?\s*to\s*(?:return|go\s*back)|will\s*(?:return|go\s*back)|want(?:s|ed)?\s*to\s*(?:return|go\s*back)|hope(?:s|d)?\s*to\s*(?:return|go\s*back)|never\s*(?:return(?:ed)?|go\s*back)|no\s*plans\s*to\s*return|stay(?:ed|ing)?\s*(?:here|permanently)|settle(?:d)?\s*down|make\s*a\s*home|visit)\b(?:[^.,;]*(?:home|sweden|old\s*country|permanently|for\s*good|temporarily|visit)[^.,;]*)?"
REGEX_IMAGE_REFERENCE = r"(?i)\b(photo(?:graph)?s?|picture(?:s)?|image(?:s)?|clipping(?:s)?|illustration(?:s)?|drawing(?:s)?|portrait(?:s)?|snapshot(?:s)?|album|scrapbook|figure|diagram|map)\b"
REGEX_TRAVEL_DURATION_TEXT = r"(?i)\b(?:(?:for|lasted|took)\s*(?:about|around|approximately\s*)?(?:a|an|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|several|few|couple\s*of)\s*(day|week|month|year|hour|minute)s?|(\d+)\s*-\s*(\d+)\s*(day|week|month|year)s|a\s*year\s*and\s*a\s*half|month\s*or\s*two|ten\s*days)\b"

# --- Helper Functions (log_message, connect_db, pre_process_date_string, normalize_date_to_iso, parse_duration_to_iso8601_string, normalize_sex_text, get_id_from_lookup, insert_new_record, extract_first_match, extract_all_matches) ---
# Keep these helper functions as they were in the previous corrected version.
# Ensure extract_first_match and extract_all_matches are the latest robust versions.
def log_message(message):
    print(f"[{datetime.now()}] {message}")

def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log_message("Successfully connected to the database.")
        return conn
    except psycopg2.Error as e:
        log_message(f"Error connecting to PostgreSQL: {e}")
        return None

def pre_process_date_string(date_str):
    if not date_str: return None
    replacements = {
        "januari": "January", "februari": "February", "mars": "March",
        "april": "April", "maj": "May", "juni": "June",
        "juli": "July", "augusti": "August", "september": "September",
        "oktober": "October", "november": "November", "december": "December"
    }
    temp_date_str = date_str
    for swe, eng in replacements.items():
        temp_date_str = re.sub(r'\b' + swe + r'\b', eng, temp_date_str, flags=re.IGNORECASE)
    return temp_date_str

def normalize_date_to_iso(date_str):
    if not date_str: return None
    processed_date_str = pre_process_date_string(date_str)
    try:
        if processed_date_str.lower() == "today": return datetime.now().strftime('%Y-%m-%d')
        if processed_date_str.lower() == "yesterday": return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if processed_date_str.lower() == "tomorrow": return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        dt_object = date_parser.parse(processed_date_str)
        return dt_object.strftime('%Y-%m-%d')
    except (ValueError, TypeError, OverflowError):
        log_message(f"Warning: Could not parse date string with dateutil: '{date_str}' (processed: '{processed_date_str}')")
        match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', processed_date_str)
        if match:
            try: return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
            except ValueError: pass
        year_match = re.search(r'\b(1[7-9]\d{2}|20\d{2})\b', processed_date_str) # Adjusted year match
        if year_match:
             log_message(f"Warning: Only year found for '{date_str}'. Storing as YYYY-01-01.")
             return f"{year_match.group(1)}-01-01"
        return None

def parse_duration_to_iso8601_string(duration_text):
    if not duration_text: return None
    duration_text_lower = duration_text.lower()

    years, months, weeks, days = 0, 0, 0, 0

    def word_to_int(word):
        if not word: return 0
        word = word.lower() # Ensure consistency
        if word.isdigit(): return int(word)
        conv = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
                "fifty": 50, "sixty": 60, "several": 3, "few": 3, "couple": 2}
        return conv.get(word, 0)

    # Check for specific complex phrases first
    if "a year and a half" in duration_text_lower:
        years = 1
        months = 6
    elif "month or two" in duration_text_lower: # Ambiguous
        months = 2 # Or 1, or log/error. Let's pick 2.
    elif "ten days" in duration_text_lower:
        days = 10
    else: # General parsing if no specific complex phrase matched
        # Regex to find number-unit pairs
        num_unit_regex = r"(\d+|a\b|an\b|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|several|few|couple(?:\s*of)?)\s*(year|month|week|day)s?"
        for match in re.finditer(num_unit_regex, duration_text_lower):
            num_str_from_match = match.group(1)
            unit_from_match = match.group(2)
            val = word_to_int(num_str_from_match)

            if unit_from_match == "year": years += val # Use += to accumulate if multiple mentions (e.g., "1 year 6 months")
            elif unit_from_match == "month": months += val
            elif unit_from_match == "week": weeks += val
            elif unit_from_match == "day": days += val

        # Handle ranges like "3-4 days" if not already captured
        if not (years or months or weeks or days):
            range_match_pattern = r"(\d+)\s*-\s*(\d+)\s*(day|week|month|year)s?"
            range_match = re.search(range_match_pattern, duration_text_lower)
            if range_match:
                num = int(range_match.group(2)) # Taking the higher end
                unit = range_match.group(3)
                if unit == "year": years = num
                elif unit == "month": months = num
                elif unit == "week": weeks = num
                elif unit == "day": days = num

    if not (years or months or weeks or days):
        log_message(f"Warning: Could not parse meaningful duration from: '{duration_text}'")
        return None

    # Construct ISO 8601 duration string
    iso_duration = "P"
    if years: iso_duration += f"{years}Y"
    if months: iso_duration += f"{months}M"
    if weeks: iso_duration += f"{weeks}W"
    if days: iso_duration += f"{days}D"

    return iso_duration if iso_duration != "P" else None

def normalize_sex_text(sex_str):
    if not sex_str: return None
    s = sex_str.lower()
    if s in ["man", "boy", "male"]: return "male"
    if s in ["woman", "girl", "female"]: return "female"
    log_message(f"Warning: Could not normalize sex text: '{sex_str}' to 'male' or 'female'")
    return None

def get_id_from_lookup(cursor, table_name, value_column_name, id_column_name, value, insert_if_missing=False):
    if value is None: return None
    try:
        lookup_value = value.lower() if isinstance(value, str) else value

        query_parts = [
            sql.SQL("SELECT {} FROM {} WHERE ").format(sql.Identifier(id_column_name), sql.Identifier(table_name))
        ]
        # Use LOWER() only if the lookup_value (and thus the column) is expected to be text
        if isinstance(lookup_value, str):
             query_parts.append(sql.SQL("LOWER({}) = %s").format(sql.Identifier(value_column_name)))
        else: # For non-string types (like integers if IDs are looked up by integer)
            query_parts.append(sql.SQL("{} = %s").format(sql.Identifier(value_column_name)))
        
        final_query = sql.Composed(query_parts)
        cursor.execute(final_query, (lookup_value,))
        result = cursor.fetchone()

        if result:
            return result[0]
        elif insert_if_missing and isinstance(value, str): # Typically only insert if the original value was a string meant for a text column
            log_message(f"Value '{value}' (normalized: '{lookup_value}') not found in {table_name}. Inserting new record.")
            insert_query = sql.SQL("INSERT INTO {} ({}) VALUES (%s) RETURNING {}").format(
                sql.Identifier(table_name),
                sql.Identifier(value_column_name),
                sql.Identifier(id_column_name)
            )
            cursor.execute(insert_query, (lookup_value,)) # Store the normalized (e.g., lowercased) value
            new_id = cursor.fetchone()[0]
            log_message(f"Inserted '{lookup_value}' into {table_name} with ID {new_id}.")
            return new_id
        else:
            log_message(f"Warning: Value '{value}' not found in lookup table '{table_name}' (insert_if_missing={insert_if_missing}).")
            return None
    except psycopg2.Error as e:
        log_message(f"Database error looking up '{value}' in '{table_name}': {e}")
        raise
    return None # Should not be reached if exception is raised

def insert_new_record(cursor, table_name, data_dict, pk_column_name):
    if not data_dict and table_name != "person_info":
        log_message(f"No data to insert into {table_name}.")
        return None
        
    if not data_dict and table_name == "person_info": # Handles person_info specifically
         cursor.execute(sql.SQL("INSERT INTO {} DEFAULT VALUES RETURNING {}").format(
            sql.Identifier(table_name), sql.Identifier(pk_column_name)))
         return cursor.fetchone()[0]
            
    cols = list(data_dict.keys()) # Ensure order for SQL construction if needed, though dicts are ordered in Py 3.7+
    vals = [data_dict.get(col) for col in cols]
    
    try:
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, cols)),
            sql.SQL(', ').join(sql.Placeholder() * len(vals)),
            sql.Identifier(pk_column_name)
        )
        cursor.execute(query, vals)
        pk_value = cursor.fetchone()[0]
        log_message(f"Inserted into {table_name} with {pk_column_name}: {pk_value}")
        return pk_value
    except psycopg2.Error as e:
        log_message(f"Error inserting into {table_name}: {e}")
        log_message(f"Data for {table_name}: {data_dict}") # Log the data that caused the error
        raise
    return None # Should not be reached if exception is raised

def extract_first_match(text, pattern, group_to_extract=None, normalizer=None):
    # log_message(f"DEBUG: extract_first_match called with pattern: {pattern[:70]}...") # Optional: log pattern entry
    match = re.search(pattern, text)
    if not match:
        return None

    value_to_process = None
    try:
        # Log the groups available for this specific match
        # This is VERY helpful for debugging "no such group"
        # log_message(f"DEBUG: Match found for pattern {pattern[:70]}... Matched text: '{match.group(0)}'. Available groups: {match.groups()}")

        if group_to_extract is not None:
            if group_to_extract == 0:
                value_to_process = match.group(0)
            # Check if the requested group_to_extract is valid for *this* match
            elif 0 < group_to_extract <= len(match.groups()):
                value_to_process = match.group(group_to_extract) # This could still be None if group captured nothing
                if value_to_process is None: # If the valid group captured None, maybe default to group(0)
                    # log_message(f"DEBUG: Group {group_to_extract} captured None for pattern {pattern[:70]}... Defaulting to group(0).")
                    value_to_process = match.group(0)
            else: # Requested group index is out of bounds for this match
                log_message(f"Warning: Requested group {group_to_extract} is out of bounds (0-{len(match.groups())}) for pattern {pattern[:70]}... Trying group 0.")
                value_to_process = match.group(0)
        else: 
            if len(match.groups()) > 0: # If there are capture groups
                # Try the first non-None capture group (index 1 onwards)
                value_to_process = next((g for g in match.groups() if g is not None), None)
                if value_to_process is None: # If all capture groups were None
                    # log_message(f"DEBUG: All capture groups were None for pattern {pattern[:70]}... Defaulting to group(0).")
                    value_to_process = match.group(0) # Fallback to full match
            else: # No capture groups in the regex pattern
                value_to_process = match.group(0)
        
        if value_to_process:
            processed_value = value_to_process.strip()
            if normalizer:
                return normalizer(processed_value)
            return processed_value
        return None

    except IndexError as e: # This specifically catches "no such group" or invalid index
        log_message(f"ERROR in extract_first_match (Pattern: {pattern[:70]}... Matched text: '{match.group(0) if match else 'NO MATCH OBJECT'}'): {e}. Groups were: {match.groups() if match else 'NO MATCH OBJECT'}")
        # Fallback to group(0) if an error occurs during group access, provided 'match' is valid
        if match:
            value_to_process = match.group(0)
            if value_to_process:
                processed_value = value_to_process.strip()
                if normalizer:
                    return normalizer(processed_value)
                return processed_value
        return None

def extract_all_matches(text, pattern, normalizer=None):
    # log_message(f"DEBUG: extract_all_matches called with pattern: {pattern[:70]}...")
    matches = re.finditer(pattern, text)
    results = set()
    for i, match_obj in enumerate(matches): # Added enumerate for match index
        value_to_add = None
        try:
            # log_message(f"DEBUG: Match {i} for pattern {pattern[:70]}... Matched text: '{match_obj.group(0)}'. Available groups: {match_obj.groups()}")
            if pattern == REGEX_NAMES:
                specific_name_match = match_obj.group(1)
                general_name_match = match_obj.group(2)
                if specific_name_match and specific_name_match.strip(): value_to_add = specific_name_match.strip()
                elif general_name_match and general_name_match.strip(): value_to_add = general_name_match.strip()
                # else: if not (specific_name_match or general_name_match) and match_obj.group(0): value_to_add = match_obj.group(0).strip() # Fallback for REGEX_NAMES too

            elif len(match_obj.groups()) > 0: # General case for other patterns
                # Iterate through captured groups (1-indexed)
                found_in_group = False
                for grp_idx in range(1, len(match_obj.groups()) + 1):
                    if match_obj.group(grp_idx) and match_obj.group(grp_idx).strip():
                        value_to_add = match_obj.group(grp_idx).strip()
                        found_in_group = True
                        break
                if not found_in_group and match_obj.group(0): # If all capture groups were None or empty
                    value_to_add = match_obj.group(0).strip()
            elif match_obj.group(0): # No capture groups in the regex pattern
                value_to_add = match_obj.group(0).strip()

            if value_to_add:
                if normalizer:
                    normalized = normalizer(value_to_add)
                    if normalized: results.add(normalized)
                else:
                    results.add(value_to_add)
        except IndexError as e: # Catch "no such group" specifically for this match_obj
             log_message(f"ERROR in extract_all_matches (Match {i}, Pattern: {pattern[:70]}... Matched text: '{match_obj.group(0) if match_obj else 'NO MATCH OBJECT'}'): {e}. Groups were: {match_obj.groups() if match_obj else 'NO MATCH OBJECT'}")
             # Optionally, add match_obj.group(0) as a fallback if appropriate for the pattern
             if match_obj and match_obj.group(0):
                value_to_add = match_obj.group(0).strip()
                if value_to_add:
                    if normalizer:
                        normalized = normalizer(value_to_add)
                        if normalized: results.add(normalized)
                    else:
                        results.add(value_to_add)
    return list(results)

# --- Main Processing Logic ---
def process_interview_file(filepath, conn):
    log_message(f"Processing file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except FileNotFoundError:
        log_message(f"Error: File not found {filepath}")
        return
    except Exception as e:
        log_message(f"Error reading file {filepath}: {e}")
        return

    processed_text = raw_text
    
    # Attempt to generate story_title from filename
    base_filename = os.path.basename(filepath)
    story_title_from_file, _ = os.path.splitext(base_filename) # Remove .txt
    story_title_from_file = story_title_from_file.replace('_', ' ').replace('-', ' ') # Basic cleaning
    if not story_title_from_file: # Fallback if filename is unusual
        story_title_from_file = "Untitled Interview " + base_filename
    log_message(f"Generated story_title: '{story_title_from_file}' from filename.")

    story_summary = processed_text[:497] + "..." if len(processed_text) > 500 else processed_text
    
    id_main_person_uuid = None
    id_demography_uuid = None
    id_travel_uuid = None
    id_text_uuid = None

    try:
        with conn.cursor() as cur:
            main_interviewee_name_text = extract_first_match(processed_text, REGEX_NAMES)
            if main_interviewee_name_text:
                id_main_person_uuid = insert_new_record(cur, "person_info", {}, "id_person")
                log_message(f"Inserted main interviewee placeholder (person_info) with id_person: {id_main_person_uuid} (based on name: '{main_interviewee_name_text}')")
            else:
                log_message(f"Warning: No main interviewee name identified in {filepath}.")

            demographic_data_to_insert = {}
            if id_main_person_uuid:
                demographic_data_to_insert['id_main_person'] = id_main_person_uuid

            sex_text_val = extract_first_match(processed_text, REGEX_SEX_TEXT)
            normalized_sex_str = normalize_sex_text(sex_text_val)
            if normalized_sex_str:
                id_sex_uuid = get_id_from_lookup(cur, "sexes", "sex", "id_sex", normalized_sex_str, insert_if_missing=True)
                if id_sex_uuid: demographic_data_to_insert['id_sex'] = id_sex_uuid
            
            age_val_str_extracted = extract_first_match(processed_text, REGEX_AGE)
            if age_val_str_extracted:
                log_message(f"Extracted age text: {age_val_str_extracted} (not stored in demographic_info as per XML).")

            marital_status_val = extract_first_match(processed_text, REGEX_MARITAL_STATUS_TEXT)
            if marital_status_val:
                id_marital_uuid = get_id_from_lookup(cur, "marital_statuses", "status", "id_marital", marital_status_val.lower(), insert_if_missing=True)
                if id_marital_uuid: demographic_data_to_insert['id_marital'] = id_marital_uuid

            education_val = extract_first_match(processed_text, REGEX_EDUCATION_TEXT)
            if education_val:
                id_education_uuid = get_id_from_lookup(cur, "education_levels", "level", "id_education", education_val.lower(), insert_if_missing=True)
                if id_education_uuid: demographic_data_to_insert['id_education'] = id_education_uuid
            
            occupation_match_obj = re.search(REGEX_OCCUPATION_TEXT, processed_text)
            if occupation_match_obj:
                occupation_text_to_lookup = (occupation_match_obj.group(1) and occupation_match_obj.group(1).strip()) or \
                                            (occupation_match_obj.group(0) and occupation_match_obj.group(0).strip())
                if occupation_text_to_lookup:
                    occupation_text_to_lookup = re.sub(r"^(?:a|an|the)\s+", "", occupation_text_to_lookup, flags=re.IGNORECASE).strip()
                    # Make sure 'occupations' table has 'occupation_name' column for lookup
                    id_occupation_uuid = get_id_from_lookup(cur, "occupations", "occupation_name", "id_occupation", occupation_text_to_lookup.lower(), insert_if_missing=True)
                    if id_occupation_uuid: demographic_data_to_insert['id_occupation'] = id_occupation_uuid
            
            religion_val = extract_first_match(processed_text, REGEX_RELIGION_TEXT)
            if religion_val:
                # Make sure 'religions' table has 'religion_name' column for lookup
                id_religion_uuid = get_id_from_lookup(cur, "religions", "religion_name", "id_religion", religion_val.lower(), insert_if_missing=True)
                if id_religion_uuid: demographic_data_to_insert['id_religion'] = id_religion_uuid

            legal_status_val = extract_first_match(processed_text, REGEX_LEGAL_STATUS_TEXT)
            if legal_status_val:
                id_legal_uuid = get_id_from_lookup(cur, "legal_statuses", "status", "id_legal", legal_status_val.lower(), insert_if_missing=True)
                if id_legal_uuid: demographic_data_to_insert['id_legal'] = id_legal_uuid

            if demographic_data_to_insert and (len(demographic_data_to_insert) > 1 or (len(demographic_data_to_insert) == 1 and 'id_main_person' in demographic_data_to_insert)):
                id_demography_uuid = insert_new_record(cur, "demographic_info", demographic_data_to_insert, "id_demography")
            else:
                log_message(f"No sufficient demographic data to insert for {filepath}.")

            if id_demography_uuid:
                all_found_names = extract_all_matches(processed_text, REGEX_NAMES)
                if main_interviewee_name_text and main_interviewee_name_text in all_found_names:
                    all_found_names.remove(main_interviewee_name_text)
                for fam_name_str in all_found_names:
                    id_fam_member_person_uuid = insert_new_record(cur, "person_info", {}, "id_person")
                    log_message(f"Inserted family member placeholder for '{fam_name_str}' (person_info) with id_person: {id_fam_member_person_uuid}")
                    if id_fam_member_person_uuid:
                        cur.execute("INSERT INTO family_link (id_demography, id_person) VALUES (%s, %s)",
                                    (id_demography_uuid, id_fam_member_person_uuid))
                        log_message(f"Linked family member {id_fam_member_person_uuid} to id_demography {id_demography_uuid}")
            
            travel_data_to_insert = {}
            departure_date_val = extract_first_match(processed_text, REGEX_DATES_TIMES, normalizer=normalize_date_to_iso)
            if departure_date_val: travel_data_to_insert['departure_date'] = departure_date_val

            departure_country_val = extract_first_match(processed_text, REGEX_LOCATIONS) # This might still pick up names
            if departure_country_val:
                # Add a check to ensure departure_country_val is not likely a person name if possible
                # For now, direct lookup
                id_country_uuid = get_id_from_lookup(cur, "countries", "country", "id_country", departure_country_val.lower(), insert_if_missing=True)
                if id_country_uuid: travel_data_to_insert['departure_country'] = id_country_uuid
                else: log_message(f"Could not find/insert country for: '{departure_country_val}'")
            
            motive_val = extract_first_match(processed_text, REGEX_MOTIVE_MIGRATION)
            if motive_val: travel_data_to_insert['motive_migration'] = motive_val

            travel_method_val = extract_first_match(processed_text, REGEX_TRAVEL_METHOD_TEXT)
            if travel_method_val:
                id_travel_method_uuid = get_id_from_lookup(cur, "travel_methods", "method", "id_travel_method", travel_method_val.lower(), insert_if_missing=True)
                if id_travel_method_uuid: travel_data_to_insert['id_travel_method'] = id_travel_method_uuid
            
            duration_text_val = extract_first_match(processed_text, REGEX_TRAVEL_DURATION_TEXT)
            parsed_duration_iso_string = parse_duration_to_iso8601_string(duration_text_val)
            if parsed_duration_iso_string:
                # Assuming travel_info.travel_duration is TEXT or VARCHAR to store ISO string.
                # If it's DATE, this assignment is incorrect and will fail or store NULL.
                travel_data_to_insert['travel_duration'] = parsed_duration_iso_string
                log_message(f"Extracted travel duration text: '{duration_text_val}', parsed as ISO: '{parsed_duration_iso_string}'.")
            else:
                 if duration_text_val: # If text was found but couldn't be parsed
                    log_message(f"Travel duration text '{duration_text_val}' found but could not be parsed to ISO 8601 string.")


            return_plans_val = extract_first_match(processed_text, REGEX_RETURN_PLANS)
            if return_plans_val: travel_data_to_insert['return_plans'] = return_plans_val

            if travel_data_to_insert:
                id_travel_uuid = insert_new_record(cur, "travel_info", travel_data_to_insert, "id_travel")
            else:
                log_message(f"No travel data extracted for {filepath}.")

            # --- 7. Insert "Interview Text" Metadata ---
            # Ensure story_title is populated HERE
            text_files_data = {
                "path": filepath,
                "story_title": story_title_from_file, # ADDED story_title
                "story_summary": story_summary,
                "id_demography": id_demography_uuid,
                "id_travel": id_travel_uuid
            }
            id_text_uuid = insert_new_record(cur, "text_files", text_files_data, "id_text")
            if not id_text_uuid:
                 raise psycopg2.Error(f"Critical error: Failed to insert text_files record for {filepath}")


            extracted_keywords_list = extract_all_matches(processed_text, REGEX_KEYWORDS, normalizer=lambda x: x.lower())
            for keyword_val in extracted_keywords_list:
                if keyword_val:
                    keyword_data = {"keyword": keyword_val, "id_text": id_text_uuid}
                    insert_new_record(cur, "keywords", keyword_data, "id_keyword")

            image_mentions_list = extract_all_matches(processed_text, REGEX_IMAGE_REFERENCE)
            if image_mentions_list:
                log_message(f"Image mentions in {filepath}: {', '.join(image_mentions_list)}. Placeholder for actual image file processing and linking.")

            conn.commit()
            log_message(f"Successfully processed and committed data for {filepath}")

    except psycopg2.Error as db_err:
        log_message(f"DATABASE ERROR for file {filepath}: {db_err}. Rolling back changes for this file.")
        if conn: conn.rollback()
    except Exception as e:
        log_message(f"UNEXPECTED ERROR processing file {filepath}: {e}. Rolling back changes for this file.")
        if conn: conn.rollback()


def main():
    text_files_dir = os.path.join("multimedia", "text")
    if not os.path.isdir(text_files_dir):
        log_message(f"Error: Directory not found: {text_files_dir}")
        return

    db_conn = connect_db()
    if not db_conn: return

    for filename in os.listdir(text_files_dir):
        if filename.lower().endswith(".txt"): # Process only .txt files
            filepath = os.path.join(text_files_dir, filename)
            process_interview_file(filepath, db_conn)
        else:
            log_message(f"Skipping non-txt file: {filename}")
    
    if db_conn:
        db_conn.close()
        log_message("Database connection closed.")

if __name__ == "__main__":
    log_message("Starting data extraction script (UUID PKs, XML Schema Priority, Story Title from Filename)...")
    main()
    log_message("Data extraction script finished.")
