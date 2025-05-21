import os
import regex as re
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "house_of_emigrants",
    "user": "postgres",
    "password": "666",
    "host": "localhost",
    "port": "5432"
}

# --- Regex Patterns (Ensure these are comprehensive and correct) ---
# Using the previously defined REGEX_* constants.
# CRITICAL: Expand Specific Names/Locations lists in REGEX_NAMES and REGEX_LOCATIONS
REGEX_NAMES = r"\b(Conrad Reinell|Annie Erickson|Jack Pennies|Mary Livingston|Leo Bing|Peter|Rich Snell Hall|Joan Crawford|Franchot Tone|Mr\. Tone|Will Rogers|Hal Moore|Evelyn Venable|Ed Garner|Axel|Ellen|Bill Warner|Dr\. Hickman|Dr\. Rieger|Florence Gustafsson|Ole Larsen|Ransom|Selma|Lex parent|Rammelisa Jansson|Elin Adele|Carl|Owen|Harold|Walter|Franz Gabrielson|Colonel Gabrielson|Miriam|Carl Anderson|Eleonora Anderson|Britta Matilda Elizabeth Olin|Gustav Vasa|Harlandqvist|Johan Andersson|Patrician Val|Ericsson|Martin|Gunnar|Nordem Highland|Adolf de Kael|Marta|Daniel|Ed Tate|Ruby Hall|Clara Lawson|Roy|Mr\. Rush|Pastor Reina Kron|Pastor Bergström|Pastor Westerberg|Rachel Sward|Pastor Ehrling|Pastor Holt|Pastor Andersson|Richard Pearson|Russell Pearson|Stephanie|Zage|Pastor Palm|Bill|Gus|Fritidsbeteget|Utvandlingsbeteget|Drottningholm|Kungsholm|Viva)\b|\b(?:(?:Mr|Mrs|Miss|Ms|Dr|Pastor|Colonel)\.?\s+)?([A-Z][a-z]+(?:(?:\s+|-)[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)?)?" # Adjusted general name to allow for middle names or two surnames
REGEX_LOCATIONS_GENERAL = r"\b([A-Z][a-z]+(?:(?:\s+|-)[A-Z][a-z]+){0,2}(?:\s+(?:County|State|Island|Yard|City|Bay|Mountains|Street|Avenue|Heights|Drive))?)\b" # General location pattern
REGEX_SPECIFIC_LOCATIONS = r"\b(Minneapolis|Iowa|Göteborg|New York|United States|Ellis Island|Chicago|Carolina|Canada|Washington|State of Washington|Buffalo|Pontiac|Detroit|Duluth|River Island|Minnesota|Wisconsin|Superior|South Superior|Illinois|Galesburg|Knoxville|Henderson County|Big River Yard|Jameson|California|New York City|Beverly Hills|Long Beach|Jamestown|Pennsylvania|Warwick|Rhode Island|Port Talcott|Providence|Salt Lake City|Hollywood|Hollywood and Vine|Brentwood Heights|England|Europe|Florida|Molin|Amerika|Lin|Lynn|Massachusetts|Owatana|Albert Lee|New Windsor|Michigan|Leamington|Ohio|LA|Winnebago|Rödön|Jämtland|Östersund|Storskön|University of Manitoba|China|Finland|Vasa|Sweden|Gulf of Bosnia|Aspås|Trondheim|Norway|Winnipeg|Klockarnäs|Nygården|Falu|Stockholm|Eriksdale|Minnadosa|Quigley Drive|Klerken|Belgium|East Flanders|West Flanders|Fourth Avenue|14th Street|East Moline|France|Davenport|Third street|Silvis|Holy Trinity|Västlanda|Westland Lutheran church|Bertranda|Adulhamn|Holdridge|Swede Bay|Binksburg|Waterbury|Bunker Hill Congregational Church|New Britain|Connecticut|Los Angeles|San Francisco|New England|Cranston|Olien|Rochester|Nebraska|Swedhåne|Malmö|Sturmsburg|Swedland|Tucson|Arizona|Norwalk|Webster|Läkontariot|Portville|Park Ridge|Schomburg|Kewani|Rockford|Decatur|Malin)\b"
REGEX_DATES_TIMES = r"(?i)\b(?:(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+the\s+\d{1,2}(?:st|nd|rd|th)?)|(?:\d{1,2}(?:st|nd|rd|th)?\s+of\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december))|(?:(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{1,2},?\s+\d{4})|(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december),?\s+\d{4}))|(?:\d{1,2}\.\s*(?:January|February|March|April|May|June|July|August|September|October|November|December|januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4})|(?:\d{4}[-/]\d{1,2}[-/]\d{1,2})|(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})|(?:(?:19|20)\d{2}s)|(?:(?:the\s+)?\d{2}s)|(?:(?:first|last|next)\s+(?:day|week|month|year|morning|night))|(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s+(?:morning|afternoon|evening|night))?)|(?:morning|afternoon|evening|night|tonight|today|yesterday|tomorrow)|(?:(?:midnight|noon))|(?:(?:\d{1,2}(?:[:.]\d{2})?)\s*o'clock)|(?:year\s+2000)|(?:(?:(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|hundreds)\s+(?:year|month|week|day|hour|minute)s?)|(?:year\s+and\s+a\s+half)|(?:month\s+or\s+two)|(?:ten\s+days)))\b"
REGEX_KEYWORDS_TEXT = r"(?i)\b(hello|yes|yeah|ja|no|cancelled|urgent)\b" # Renamed for clarity
REGEX_SEX_TEXT = r"(?i)\b(male|female|man|woman|boy|girl)\b"
REGEX_MARITAL_STATUS_TEXT = r"(?i)\b(single|married|divorced|separated|widow(?:ed)?|engaged)\b"
REGEX_EDUCATION_TEXT = r"(?i)\b(grade\s*school|primary\s*school|some\s*secondary\s*school|completed\s*secondary\s*school|high\s*school|evening\s*school|business\s*course|trade\s*or\s*vocational\s*training|some\s*college(?:/university)?|completed\s*college(?:/university)?|university|educated|learned\s*to|studied|degree\s*(?:in\s*\w+)?|diploma|illiterate|did\s*not\s*finish\s*(?:high\s*)?school|went\s*to\s*school\s*(?:in|at)?|took\s*grades\s*\w+\s*to\s*\w+)\b" # Added from lookup
REGEX_OCCUPATION_TEXT = r"(?i)\b(?:worked\s*(?:as\s*a|in\s*a|for)?|job\s*(?:was|is)|occupation\s*(?:is|was)|I\s*(?:am|was)\s*a(?:n)?|my\s*profession\s*(?:is|was)|profession\s*of)\s*([a-zA-Z\s\-.,]+(?:(?:\s*|-)(?:man|woman|worker|operator|maker|keeper|master|hand|laborer|smith|wright|monger|ster))?)\b|\b(pastor|minister|priest|rabbi|imam|doctor|surgeon|physician|nurse|teacher|professor|educator|engineer|architect|designer|developer|programmer|analyst|scientist|researcher|lawyer|attorney|judge|paralegal|accountant|auditor|consultant|manager|director|supervisor|foreman|executive|administrator|clerk|secretary|assistant|receptionist|writer|author|editor|journalist|reporter|artist|musician|actor|performer|dancer|designer|photographer|farmer|rancher|gardener|forester|fisherman|hunter|chef|cook|baker|waiter|waitress|bartender|hostess|carpenter|plumber|electrician|mechanic|technician|operator|machinist|welder|builder|constructor|laborer|driver|pilot|captain|sailor|merchant|vendor|salesman|saleswoman|retailer|shopkeeper|cashier|librarian|curator|archivist|police\s*officer|firefighter|soldier|military|officer|guard|janitor|custodian|cleaner|housekeeper|maid|nanny|caregiver|volunteer|student|apprentice|intern|retired|unemployed|homemaker|housewife|soccer-stien|conductor|tool\s*and\s*die\s*maker|lathe\s*operator|molder|aviator|car\s*salesman)\b" # Added comma to char class
REGEX_RELIGION_TEXT = r"(?i)\b(Lutheran|Catholic|Jewish|Protestant|Baptist|Methodist|Presbyterian|Episcopalian|Evangelical|Pentecostal|Mormon|Latter-day\s*Saints|Jehovah's\s*Witness|Seventh-day\s*Adventist|Adventist|Quaker|Mennonite|Amish|Christian|Islam|Muslim|Hindu|Buddhist|Sikh|Bahá'í|Atheist|Agnostic|Covenant\s*Church|Mission\s*Church|Congregational\s*Church|Salvation\s*Army)\b"
REGEX_LEGAL_STATUS_TEXT = r"(?i)\b(citizen\s*of\s*origin\s*country|stateless|refugee|asylum\s*seeker|undocumented|naturalized\s*citizen|legal\s*immigrant|temporary\s*resident|immigrant|emigrant|migrant|visa\s*(?:holder)?|green\s*card|permanent\s*resident|naturalized|alien|non-resident|papers|Fritidsbeteget|Utvandlingsbeteget|civiliseringar|quota)\b" # Added from lookup
REGEX_MOTIVE_MIGRATION_TEXT = r"(?i)\b(economic\s*opportunity|family\s*reunification|religious\s*persecution|political\s*persecution|war/conflict|famine\s*or\s*natural\s*disaster|education|adventure|land\s*ownership|forced\s*migration|motive\s*(?:for|was)|reason\s*(?:for|was)|came\s*(?:for|because|to)|left\s*(?:for|because|to)|migrated\s*(?:for|because|to)|moved\s*(?:for|because|to)|seeking|in\s*search\s*of|escape\s*(?:from)?|due\s*to|opportunity|better\s*life|economic\s*reasons|political\s*reasons|religious\s*reasons|reunite\s*with\s*family|join\s*family|employment|work|job|hard\s*times|no\s*work|famine|war|persecution|studies|health\s*reasons|climate|land|gold\s*rush|quota\s*(?:was\s*opened)?)\b(?:[^.,;]*(?:work|job|opportunities|family|freedom|war|famine|persecution|better\s*life|economic\s*conditions|studies|health)[^.,;]*)?" # Added from lookup, combined
REGEX_TRAVEL_METHOD_TEXT = r"(?i)\b(steamship|sailboat|train|horse-drawn\s*carriage|on\s*foot|walked|wagon\s*or\s*cart|automobile|car|ship|steamer|boat|vessel|ferry|liner|sailed\s*on|went\s*on|railroad|railway|by\s*rail|bus|coach|airplane|aeroplane|by\s*air|flew\s*on|horseback|Drottningholm|Kungsholm|Stockholm|Viva)\b" # Added from lookup, combined
REGEX_RETURN_PLANS = r"(?i)\b(?:plan(?:s|ned)?\s*(?:to\s*return|to\s*go\s*back)|intend(?:s|ed)?\s*to\s*(?:return|go\s*back)|will\s*(?:return|go\s*back)|want(?:s|ed)?\s*to\s*(?:return|go\s*back)|hope(?:s|d)?\s*to\s*(?:return|go\s*back)|never\s*(?:return(?:ed)?|go\s*back)|no\s*plans\s*to\s*return|stay(?:ed|ing)?\s*(?:here|permanently)|settle(?:d)?\s*down|make\s*a\s*home|visit)\b(?:[^.,;]*(?:home|sweden|old\s*country|permanently|for\s*good|temporarily|visit)[^.,;]*)?"
REGEX_IMAGE_REFERENCE = r"(?i)\b(photo(?:graph)?s?|picture(?:s)?|image(?:s)?|clipping(?:s)?|illustration(?:s)?|drawing(?:s)?|portrait(?:s)?|snapshot(?:s)?|album|scrapbook|figure|diagram|map)\b"
REGEX_TRAVEL_DURATION_TEXT = r"(?i)\b(?:(?:for|lasted|took)\s*(?:about|around|approximately\s*)?(?:a|an|\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|several|few|couple\s*of)\s*(day|week|month|year|hour|minute)s?|(\d+)\s*-\s*(\d+)\s*(day|week|month|year)s?|a\s*year\s*and\s*a\s*half|month\s*or\s*two|ten\s*days)\b" # Added s? to range unit

# --- Helper Functions ---
# (Keep log_message, connect_db, pre_process_date_string, normalize_date_to_iso, 
#  normalize_sex_text, insert_new_record, extract_first_match, extract_all_matches
#  from the previous version. Ensure parse_duration_to_iso8601_string is the robust one.)

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
        year_match = re.search(r'\b(1[7-9]\d{2}|20\d{2})\b', processed_date_str)
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
        word = word.lower() 
        if word.isdigit(): return int(word)
        conv = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
                "fifty": 50, "sixty": 60, "several": 3, "few": 3, "couple": 2}
        return conv.get(word, 0)

    processed_by_specific_phrase = False
    if "a year and a half" in duration_text_lower:
        years = 1; months = 6; processed_by_specific_phrase = True
    elif "month or two" in duration_text_lower:
        months = 2; processed_by_specific_phrase = True # Or 1, decided on 2
    elif "ten days" in duration_text_lower:
        days = 10; processed_by_specific_phrase = True
    
    if not processed_by_specific_phrase:
        num_unit_regex = r"(\d+|a\b|an\b|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|several|few|couple(?:\s*of)?)\s*(year|month|week|day)s?"
        temp_years, temp_months, temp_weeks, temp_days = 0,0,0,0
        for match in re.finditer(num_unit_regex, duration_text_lower):
            num_str_from_match = match.group(1)
            unit_from_match = match.group(2)
            val = word_to_int(num_str_from_match)
            if unit_from_match == "year": temp_years += val
            elif unit_from_match == "month": temp_months += val
            elif unit_from_match == "week": temp_weeks += val
            elif unit_from_match == "day": temp_days += val
        if temp_years: years = temp_years # Accumulate if specific phrases didn't set them
        if temp_months: months = temp_months
        if temp_weeks: weeks = temp_weeks
        if temp_days: days = temp_days
        
        if not (years or months or weeks or days): # Check range if nothing else found
            range_match_pattern = r"(\d+)\s*-\s*(\d+)\s*(day|week|month|year)s?"
            range_match = re.search(range_match_pattern, duration_text_lower)
            if range_match:
                num = int(range_match.group(2))
                unit = range_match.group(3)
                if unit == "year": years = num
                elif unit == "month": months = num
                elif unit == "week": weeks = num
                elif unit == "day": days = num
    
    if not (years or months or weeks or days):
        log_message(f"Warning: Could not parse meaningful duration from: '{duration_text}'")
        return None

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
        lookup_value = value.lower().strip() if isinstance(value, str) else value

        query_parts = [
            sql.SQL("SELECT {} FROM {} WHERE ").format(sql.Identifier(id_column_name), sql.Identifier(table_name))
        ]
        if isinstance(lookup_value, str):
             query_parts.append(sql.SQL("LOWER({}) = %s").format(sql.Identifier(value_column_name)))
        else:
            query_parts.append(sql.SQL("{} = %s").format(sql.Identifier(value_column_name)))
        
        final_query = sql.Composed(query_parts)
        cursor.execute(final_query, (lookup_value,))
        result = cursor.fetchone()

        if result:
            return result[0]
        elif insert_if_missing and isinstance(value, str) and lookup_value: # Ensure lookup_value is not empty
            log_message(f"Value '{value}' (normalized: '{lookup_value}') not found in {table_name}. Inserting new record.")
            insert_query = sql.SQL("INSERT INTO {} ({}) VALUES (%s) RETURNING {}").format(
                sql.Identifier(table_name), sql.Identifier(value_column_name), sql.Identifier(id_column_name)
            )
            cursor.execute(insert_query, (lookup_value,))
            new_id = cursor.fetchone()[0]
            log_message(f"Inserted '{lookup_value}' into {table_name} with ID {new_id}.")
            return new_id
        else:
            if not (isinstance(value, str) and lookup_value) and insert_if_missing :
                 log_message(f"Warning: Value '{value}' is not a non-empty string. Not inserting into lookup table '{table_name}'.")
            else:
                 log_message(f"Warning: Value '{value}' not found in lookup table '{table_name}' (insert_if_missing={insert_if_missing}).")
            return None
    except psycopg2.Error as e:
        log_message(f"Database error looking up '{value}' in '{table_name}': {e}")
        raise
    return None

def insert_new_record(cursor, table_name, data_dict, pk_column_name):
    if not data_dict and table_name != "person_info": # person_info can be inserted with DEFAULT VALUES
        # For tables like demographic_info, travel_info, if data_dict is empty, it means no relevant data was found.
        # We might still need to insert a row if it's referenced by a NOT NULL FK in text_files (e.g., id_demography)
        # This logic is handled by the `id_demography NOT NULL` in text_files which means demo MUST be inserted.
        if table_name == "demographic_info" and 'id_main_person' not in data_dict: # Avoid inserting empty demo if no main person
             log_message(f"Skipping insert for {table_name} as it's empty and no main person ID.")
             return None
        # If we must insert (e.g. for demographic_info when text_files.id_demography is NOT NULL)
        # Then we insert with just the default PK, other fields will be NULL
        if table_name in ["demographic_info"]: # Add other tables that must be inserted even if empty
            log_message(f"Data_dict for {table_name} is empty, but inserting with default PK due to schema requirements.")
            cursor.execute(sql.SQL("INSERT INTO {} DEFAULT VALUES RETURNING {}").format(
                sql.Identifier(table_name), sql.Identifier(pk_column_name)))
            return cursor.fetchone()[0]

        log_message(f"No data to insert into {table_name} (and not person_info or mandatory empty).")
        return None
        
    if not data_dict and table_name == "person_info": # Handles person_info specifically
         cursor.execute(sql.SQL("INSERT INTO {} DEFAULT VALUES RETURNING {}").format(
            sql.Identifier(table_name), sql.Identifier(pk_column_name)))
         return cursor.fetchone()[0]
            
    cols = list(data_dict.keys())
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
        log_message(f"Data for {table_name}: {data_dict}")
        raise
    return None

def extract_first_match(text, pattern, group_to_extract=None, normalizer=None):
    match = re.search(pattern, text)
    if not match: return None
    value_to_process = None
    try:
        if group_to_extract is not None:
            if group_to_extract == 0: value_to_process = match.group(0)
            elif 0 < group_to_extract <= len(match.groups()) and match.group(group_to_extract) is not None:
                value_to_process = match.group(group_to_extract)
            else:
                # log_message(f"Warning: Requested group {group_to_extract} invalid or None for pattern {pattern[:70]}... Trying group 0.")
                value_to_process = match.group(0) 
        else: 
            if len(match.groups()) > 0:
                value_to_process = next((g for g in match.groups() if g is not None), match.group(0))
            else: value_to_process = match.group(0)
        
        if value_to_process:
            processed_value = value_to_process.strip()
            if normalizer: return normalizer(processed_value)
            return processed_value
        return None
    except IndexError: 
        log_message(f"Error ('no such group' likely) for pattern {pattern[:70]}... Defaulting to full match.")
        value_to_process = match.group(0)
        if value_to_process:
            processed_value = value_to_process.strip()
            if normalizer: return normalizer(processed_value)
            return processed_value
        return None

def extract_all_matches(text, pattern, normalizer=None):
    matches = re.finditer(pattern, text)
    results = set()
    for match_obj in matches:
        value_to_add = None
        if pattern == REGEX_NAMES:
            # REGEX_NAMES = r"\b(Specific List)\b|\b(?:(OptionalTitlePart))?([GeneralNamePart])\b"
            # Group 1: Specific Names List
            # Group 2: General Name Part (after optional non-capturing title)
            specific_name_match = match_obj.group(1)
            general_name_match = match_obj.group(2) # This is the one for the general name pattern
            if specific_name_match and specific_name_match.strip(): value_to_add = specific_name_match.strip()
            elif general_name_match and general_name_match.strip(): value_to_add = general_name_match.strip()
        elif pattern == REGEX_LOCATIONS_GENERAL or pattern == REGEX_SPECIFIC_LOCATIONS:
             # REGEX_LOCATIONS_GENERAL = r"\b([A-Z][a-z]+(?:...))\b" -> group(1) is the location
             # REGEX_SPECIFIC_LOCATIONS = r"\b(Minneapolis|...)\b" -> group(1) is the location
            if match_obj.group(1) and match_obj.group(1).strip():
                value_to_add = match_obj.group(1).strip()
            elif match_obj.group(0) : # Fallback if group 1 is None but full match exists
                value_to_add = match_obj.group(0).strip()

        elif len(match_obj.groups()) > 0: # General case for other patterns
            value_to_add = next((g for g in match_obj.groups() if g and g.strip()), None)
            if not value_to_add and match_obj.group(0): value_to_add = match_obj.group(0).strip()
        elif match_obj.group(0): value_to_add = match_obj.group(0).strip()

        if value_to_add:
            if normalizer:
                normalized = normalizer(value_to_add)
                if normalized: results.add(normalized)
            else:
                results.add(value_to_add)
    return list(results)

def extract_person_name_parts(full_name_str):
    """Extracts first_name and first_surname from a full name string."""
    if not full_name_str:
        return None, None
    parts = full_name_str.strip().split()
    first_name = None
    first_surname = None
    if len(parts) == 1:
        first_name = parts[0] # Or assume it's a surname if only one word? Context needed.
                            # For now, assume single word is first name.
    elif len(parts) > 1:
        first_name = parts[0]
        first_surname = " ".join(parts[1:]) # Handles multi-word surnames
    return first_name, first_surname

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
    base_filename = os.path.basename(filepath)
    story_title_from_file, _ = os.path.splitext(base_filename)
    story_title_from_file = story_title_from_file.replace('_', ' ').replace('-', ' ')
    if not story_title_from_file: story_title_from_file = "Untitled Interview " + base_filename
    # log_message(f"Generated story_title: '{story_title_from_file}' from filename.") # Already logged if needed

    story_summary = processed_text[:497] + "..." if len(processed_text) > 500 else processed_text

    id_main_person_uuid = None
    id_demography_uuid = None
    id_travel_uuid = None
    id_text_uuid = None

    try:
        with conn.cursor() as cur:
            # --- Person Info (Main Interviewee) ---
            main_interviewee_full_name = extract_first_match(processed_text, REGEX_NAMES)
            person_data_to_insert = {}
            if main_interviewee_full_name:
                first_name, first_surname = extract_person_name_parts(main_interviewee_full_name)
                if first_name: person_data_to_insert['first_name'] = first_name
                if first_surname: person_data_to_insert['first_surname'] = first_surname

            id_main_person_uuid = insert_new_record(cur, "person_info", person_data_to_insert, "id_person")
            if id_main_person_uuid:
                log_message(f"Inserted main interviewee (person_info) ID: {id_main_person_uuid} (Name: '{main_interviewee_full_name}')")
            else:
                log_message(f"CRITICAL: Failed to insert main person_info for {filepath}. Skipping file.")
                raise psycopg2.Error("Failed to create main person_info record.")

            # --- Demographic Info ---
            demographic_data_to_insert = {}
            if id_main_person_uuid:
                demographic_data_to_insert['id_main_person'] = id_main_person_uuid

            sex_text_val = extract_first_match(processed_text, REGEX_SEX_TEXT)
            normalized_sex_str = normalize_sex_text(sex_text_val)
            if normalized_sex_str:
                id_sex_val = get_id_from_lookup(cur, "sexes", "sex", "id_sex", normalized_sex_str, insert_if_missing=False)
                if id_sex_val: demographic_data_to_insert['id_sex'] = id_sex_val

            marital_status_val = extract_first_match(processed_text, REGEX_MARITAL_STATUS_TEXT)
            if marital_status_val:
                id_marital_val = get_id_from_lookup(cur, "marital_statuses", "status", "id_marital", marital_status_val.lower(), insert_if_missing=False)
                if id_marital_val: demographic_data_to_insert['id_marital'] = id_marital_val

            education_val = extract_first_match(processed_text, REGEX_EDUCATION_TEXT)
            if education_val:
                id_education_val = get_id_from_lookup(cur, "education_levels", "level", "id_education", education_val.lower(), insert_if_missing=False)
                if id_education_val: demographic_data_to_insert['id_education'] = id_education_val

            # ---- REMOVED OCCUPATION EXTRACTION ----
            # occupation_match_obj = re.search(REGEX_OCCUPATION_TEXT, processed_text)
            # if occupation_match_obj:
            #     occupation_text_to_lookup = (occupation_match_obj.group(1) and occupation_match_obj.group(1).strip()) or \
            #                                 (occupation_match_obj.group(0) and occupation_match_obj.group(0).strip())
            #     if occupation_text_to_lookup:
            #         occupation_text_to_lookup = re.sub(r"^(?:a|an|the)\s+", "", occupation_text_to_lookup, flags=re.IGNORECASE).strip()
            #         id_occupation_val = get_id_from_lookup(cur, "occupations", "occupation_name", "id_occupation", occupation_text_to_lookup.lower(), insert_if_missing=True)
            #         if id_occupation_val: demographic_data_to_insert['id_occupation'] = id_occupation_val
            log_message(f"Skipping occupation extraction for {filepath} as per new requirement.")

            # ---- REMOVED RELIGION EXTRACTION ----
            # religion_val = extract_first_match(processed_text, REGEX_RELIGION_TEXT)
            # if religion_val:
            #     id_religion_val = get_id_from_lookup(cur, "religions", "religion_name", "id_religion", religion_val.lower(), insert_if_missing=True)
            #     if id_religion_val: demographic_data_to_insert['id_religion'] = id_religion_val
            log_message(f"Skipping religion extraction for {filepath} as per new requirement.")

            legal_status_val = extract_first_match(processed_text, REGEX_LEGAL_STATUS_TEXT)
            if legal_status_val:
                id_legal_val = get_id_from_lookup(cur, "legal_statuses", "status", "id_legal", legal_status_val.lower(), insert_if_missing=False)
                if id_legal_val: demographic_data_to_insert['id_legal'] = id_legal_val

            id_demography_uuid = insert_new_record(cur, "demographic_info", demographic_data_to_insert, "id_demography")
            if not id_demography_uuid:
                raise psycopg2.Error(f"Failed to insert demographic_info for {filepath}")

            # --- Mention Link ---
            if id_demography_uuid:
                all_mentioned_names = extract_all_matches(processed_text, REGEX_NAMES)
                if main_interviewee_full_name and main_interviewee_full_name in all_mentioned_names:
                    all_mentioned_names.remove(main_interviewee_full_name)

                for name_str in all_mentioned_names:
                    mention_person_data = {}
                    first_name, first_surname = extract_person_name_parts(name_str)
                    if first_name: mention_person_data['first_name'] = first_name
                    if first_surname: mention_person_data['first_surname'] = first_surname

                    id_mentioned_person_uuid = insert_new_record(cur, "person_info", mention_person_data, "id_person")
                    if id_mentioned_person_uuid:
                        # log_message(f"Inserted mentioned person '{name_str}' (person_info) ID: {id_mentioned_person_uuid}")
                        try:
                            cur.execute("INSERT INTO mention_link (id_demography, id_person) VALUES (%s, %s) ON CONFLICT DO NOTHING", # Added ON CONFLICT
                                        (id_demography_uuid, id_mentioned_person_uuid))
                            # log_message(f"Linked mentioned person {id_mentioned_person_uuid} to id_demography {id_demography_uuid}")
                        except psycopg2.Error as ie: # Error variable changed to avoid conflict
                             log_message(f"Error inserting into mention_link for demography {id_demography_uuid}, person {id_mentioned_person_uuid}: {ie}")
                             # No explicit rollback here for mention_link, main transaction will handle it
                    # else: # This else might be too noisy if many names are extracted but not relevant
                        # log_message(f"Warning: Failed to insert person_info for mentioned name '{name_str}'.")


            # --- Travel Info ---
            travel_data_to_insert = {}
            departure_date_val = extract_first_match(processed_text, REGEX_DATES_TIMES, normalizer=normalize_date_to_iso)
            if departure_date_val: travel_data_to_insert['departure_date'] = departure_date_val

            destination_location_text = extract_first_match(processed_text, REGEX_SPECIFIC_LOCATIONS)
            if not destination_location_text:
                destination_location_text = extract_first_match(processed_text, REGEX_LOCATIONS_GENERAL)

            if destination_location_text:
                # log_message(f"Potential destination city text: {destination_location_text}")
                id_country_for_city = None
                # Try to infer country from a broader context or a specific "country" regex match
                country_for_city_text = extract_first_match(processed_text, REGEX_SPECIFIC_LOCATIONS, normalizer=lambda x: x.lower()) # Try specific countries
                # A more dedicated country regex might be better than reusing general locations

                if country_for_city_text: # Simple check: if the extracted location is a known country
                    is_a_country_check = get_id_from_lookup(cur, "countries", "country", "id_country", country_for_city_text)
                    if is_a_country_check:
                        id_country_for_city = is_a_country_check
                    # else: not a known country, might be a city in an unknown country

                city_data = {"city": destination_location_text.lower()}
                if id_country_for_city:
                    city_data["id_country"] = id_country_for_city

                existing_city_id = None
                city_query_parts = [sql.SQL("SELECT id_city FROM cities WHERE LOWER(city) = %s")]
                city_query_params = [destination_location_text.lower()]
                if id_country_for_city:
                    city_query_parts.append(sql.SQL(" AND id_country = %s"))
                    city_query_params.append(id_country_for_city)
                else:
                    city_query_parts.append(sql.SQL(" AND id_country IS NULL")) # Important for cities without known country

                cur.execute(sql.Composed(city_query_parts), tuple(city_query_params))
                res = cur.fetchone()
                if res: existing_city_id = res[0]

                if existing_city_id:
                    id_city_uuid = existing_city_id
                    # log_message(f"Found existing city '{destination_location_text}' with ID {id_city_uuid}")
                else:
                    id_city_uuid = insert_new_record(cur, "cities", city_data, "id_city")
                    # log_message(f"Inserted city '{destination_location_text}' with ID {id_city_uuid}")
                if id_city_uuid: travel_data_to_insert['destination_city'] = id_city_uuid


            motive_text_val = extract_first_match(processed_text, REGEX_MOTIVE_MIGRATION_TEXT)
            if motive_text_val:
                primary_motive_term = motive_text_val.split()[0].lower() if motive_text_val else None
                if primary_motive_term: # Ensure there is a term to lookup
                    id_motive_val = get_id_from_lookup(cur, "motives_migration", "motive", "id_motive", primary_motive_term, insert_if_missing=False)
                    if id_motive_val:
                        travel_data_to_insert['id_motive_migration'] = id_motive_val
                    # else: # Too noisy to log every non-match for motive term
                        # log_message(f"Motive text '{motive_text_val}' found, but term '{primary_motive_term}' not in motives_migration lookup.")

            duration_text_val = extract_first_match(processed_text, REGEX_TRAVEL_DURATION_TEXT)
            parsed_duration_iso_string = parse_duration_to_iso8601_string(duration_text_val)
            if parsed_duration_iso_string:
                travel_data_to_insert['travel_duration'] = parsed_duration_iso_string

            return_plans_val = extract_first_match(processed_text, REGEX_RETURN_PLANS)
            if return_plans_val: travel_data_to_insert['return_plans'] = return_plans_val

            if travel_data_to_insert:
                id_travel_uuid = insert_new_record(cur, "travel_info", travel_data_to_insert, "id_travel")
            # else: # No need to log this if no travel data, id_travel_uuid will remain None
                # log_message(f"No travel data extracted for {filepath}.")


            if id_travel_uuid:
                travel_method_texts = extract_all_matches(processed_text, REGEX_TRAVEL_METHOD_TEXT)
                for method_text in travel_method_texts:
                    id_travel_method_val = get_id_from_lookup(cur, "travel_methods", "method", "id_travel_method", method_text.lower(), insert_if_missing=False)
                    if id_travel_method_val:
                        try:
                            cur.execute("INSERT INTO travel_link (id_travel, id_travel_method) VALUES (%s, %s) ON CONFLICT DO NOTHING", # Added ON CONFLICT
                                        (id_travel_uuid, id_travel_method_val))
                            # log_message(f"Linked travel method '{method_text}' to id_travel {id_travel_uuid}")
                        except psycopg2.Error as ie_travel_link:
                             log_message(f"Error inserting into travel_link for travel {id_travel_uuid}, method {id_travel_method_val}: {ie_travel_link}")

            text_files_data = {
                "path": filepath, "story_title": story_title_from_file,
                "story_summary": story_summary, "id_demography": id_demography_uuid, # Must have id_demography
                "id_travel": id_travel_uuid # Can be NULL
            }
            id_text_uuid = insert_new_record(cur, "text_files", text_files_data, "id_text")
            if not id_text_uuid:
                 raise psycopg2.Error(f"CRITICAL: Failed to insert text_files record for {filepath}")

            extracted_keywords_list = extract_all_matches(processed_text, REGEX_KEYWORDS_TEXT, normalizer=lambda x: x.lower())
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
        log_message(f"UNEXPECTED ERROR processing file {filepath}: {type(e).__name__} - {e}. Rolling back changes for this file.") # Log type of exception
        if conn: conn.rollback()


# --- main() function and if __name__ == "__main__": block remain the same ---
def main():
    text_files_dir = os.path.join("multimedia", "text")
    if not os.path.isdir(text_files_dir):
        log_message(f"Error: Directory not found: {text_files_dir}")
        return

    db_conn = connect_db()
    if not db_conn: return

    for filename in os.listdir(text_files_dir):
        if filename.lower().endswith(".txt"):
            filepath = os.path.join(text_files_dir, filename)
            process_interview_file(filepath, db_conn)
        else:
            log_message(f"Skipping non-txt file: {filename}")

    if db_conn:
        db_conn.close()
        log_message("Database connection closed.")

if __name__ == "__main__":
    log_message("Starting data extraction script (V4 - No Occupation/Religion)...")
    main()
    log_message("Data extraction script finished.")
