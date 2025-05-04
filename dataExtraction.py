import spacy
import re
import json
import sys
import yake
import psycopg
from psycopg import sql
from spacy.pipeline import EntityRuler

# ——— Database settings ———
DB_PARAMS = {
    "dbname":   "house_of_emigrants",
    "user":     "postgres",
    "password": "666",
    "host":     "localhost",
    "port":     "5432"
}

def get_db_connection():
    return psycopg.connect(**DB_PARAMS)

# ——— NLP setup ———
def crear_pipeline(nlp):
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    patterns = [
        {"label":"DATE", "pattern":[{"TEXT":{"REGEX":r"\d{4}-\d{2}-\d{2}"}}]},
        {"label":"BIRTHDATE", "pattern":[
            {"TEXT":{"REGEX":r"\d{4}-\d{2}-\d{2}"}},
        ]},
        {"label":"ADDRESS", "pattern":[
            {"TEXT":{"REGEX":r"\d+"}},{"OP":"+"},
            {"TEXT":{"REGEX":r"[A-Za-z]+"}},
            {"TEXT":{"REGEX":r"(Avenue|Street|Road|Blvd|vägen|gatan)"}}                                                                      
        ]}
    ]
    ruler.add_patterns(patterns)
    return nlp

def extract_keywords(text):
    kw = yake.KeywordExtractor(lan="en", n=1, dedupLim=0.9, top=10)
    kws = [phrase.lower() for phrase, score in kw.extract_keywords(text)]
    return list(dict.fromkeys(kws))

def extraer_datos(texto, nlp):
    doc = nlp(texto)
    datos = {
        "fechas": [],
        "nombres": [],
        "direcciones": [],
        "fechas_nac": [],
        "palabras_clave": []
    }
    for ent in doc.ents:
        if ent.label_ == "DATE" and re.match(r"\d{4}-\d{2}-\d{2}", ent.text):
            datos["fechas"].append(ent.text)
        if ent.label_ == "PERSON":
            datos["nombres"].append(ent.text)
        if ent.label_ == "ADDRESS":
            datos["direcciones"].append(ent.text)
        if ent.label_ == "BIRTHDATE":
            datos["fechas_nac"].append(ent.text)
    datos["palabras_clave"] = extract_keywords(texto)
    # dedupe names
    datos["nombres"] = list(dict.fromkeys(datos["nombres"]))
    return datos

# ——— Persistence ———
def store_to_db(texto, datos):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1) Insert persona (take first name as nombre, rest as apellido)
        if datos["nombres"]:
            parts = datos["nombres"][0].split(None, 1)
            nombre   = parts[0]
            apellido = parts[1] if len(parts)>1 else ""
        else:
            nombre, apellido = ("Desconocido","")
        fecha_nac = datos["fechas_nac"][0] if datos["fechas_nac"] else None

        cur.execute(
            sql.SQL("""
              INSERT INTO personas (nombre, apellido, fecha_nacimiento)
              VALUES (%s, %s, %s)
              RETURNING persona_id
            """),
            [nombre, apellido, fecha_nac]
        )
        persona_id = cur.fetchone()[0]

        # 2) Insert relato
        fecha_relato = datos["fechas"][0] if datos["fechas"] else None
        titulo = texto[:50] + "..."  # first 50 chars
        cur.execute(
            sql.SQL("""
              INSERT INTO relatos_emigracion (persona_id, texto_relato, fecha_relato, titulo_relato)
              VALUES (%s, %s, %s, %s)
              RETURNING relato_id
            """),
            [persona_id, texto, fecha_relato, titulo]
        )
        relato_id = cur.fetchone()[0]

        # 3) For each keyword: upsert in palabras_clave, then link
        for kw in datos["palabras_clave"]:
            # upsert palabra
            cur.execute(
                sql.SQL("""
                  INSERT INTO palabras_clave (palabra)
                  VALUES (%s)
                  ON CONFLICT (palabra) DO UPDATE SET palabra = EXCLUDED.palabra
                  RETURNING palabra_clave_id
                """),
                [kw]
            )
            # if insert did nothing, fetch existing id
            res = cur.fetchone()
            if res:
                pk_id = res[0]
            else:
                cur.execute(
                    sql.SQL("SELECT palabra_clave_id FROM palabras_clave WHERE palabra = %s"),
                    [kw]
                )
                pk_id = cur.fetchone()[0]

            # count occurrences for frecuencia
            freq = len(re.findall(rf"\b{re.escape(kw)}\b", texto, flags=re.IGNORECASE))
            cur.execute(
                sql.SQL("""
                  INSERT INTO relatos_palabras (relato_id, palabra_clave_id, frecuencia)
                  VALUES (%s, %s, %s)
                """),
                [relato_id, pk_id, freq]
            )

        conn.commit()
        print(f"Inserted persona {persona_id}, relato {relato_id}, {len(datos['palabras_clave'])} keywords.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def main(input_file):
    # Load and extract
    nlp = spacy.load("en_core_web_md")
    nlp = crear_pipeline(nlp)
    texto = open(input_file, "r", encoding="utf-8").read()
    datos = extraer_datos(texto, nlp)

    # Print extracted for debug
    print(json.dumps(datos, indent=2, ensure_ascii=False))

    # Store into DB
    store_to_db(texto, datos)

if __name__ == "__main__":
    if len(sys.argv)!=2:
        print("Usage: python dataExtraction.py <input.txt>")
        sys.exit(1)
    main(sys.argv[1])
