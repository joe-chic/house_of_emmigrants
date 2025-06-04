from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)
from psycopg import sql
import psycopg
import os
import json
import subprocess
from deep_translator import GoogleTranslator
from functools import lru_cache

app = Flask(__name__)
app.secret_key = "a12f9c2b4d5e6f7g8h9i0jklmnopqrst"  # Needed for flashing messages

# Idioma predeterminado y configuración
LANGUAGES = {"en": "English", "es": "Español"}
DEFAULT_LANGUAGE = "en"


# Detect touch devices
def is_touch_device():
    # Verificar si el usuario ha forzado un modo específico
    if "force_touch" in session:
        return session["force_touch"]

    # Detectar dispositivos táctiles de forma normal
    user_agent = request.headers.get("User-Agent", "").lower()
    return (
        "mobile" in user_agent
        or "android" in user_agent
        or "iphone" in user_agent
        or "ipad" in user_agent
    )


# --- Multimedia serving ---
@app.route("/multimedia/<path:filename>")
def serve_multimedia(filename):
    return send_from_directory("multimedia", filename)


# --- Funciones de traducción ---
@lru_cache(maxsize=1000)
def translate_text(text, target_lang):
    """Traduce texto al idioma especificado usando caché para eficiencia"""
    if not text or target_lang == DEFAULT_LANGUAGE:
        return text

    try:
        translator = GoogleTranslator(source="auto", target=target_lang)
        return translator.translate(text)
    except Exception as e:
        print(f"Error al traducir: {e}")
        return text


def get_current_language():
    """Obtiene el idioma actual de la sesión o el predeterminado"""
    return session.get("language", DEFAULT_LANGUAGE)


@app.route("/switch_language/<lang>")
def switch_language(lang):
    """Cambia el idioma de la sesión"""
    if lang in LANGUAGES:
        session["language"] = lang
    return redirect(request.referrer or url_for("homepage"))


# Función para procesar y traducir datos del dashboard
def process_dashboard_data(data, target_lang):
    """Traduce los datos del dashboard al idioma especificado"""
    if target_lang == DEFAULT_LANGUAGE:
        return data

    translated_data = {}

    # Traducir palabras clave
    if "wf_words" in data:
        translated_data["wf_words"] = [
            translate_text(word, target_lang) for word in data["wf_words"]
        ]

    # Traducir países/ciudades
    if "geo_countries" in data:
        translated_data["geo_countries"] = [
            translate_text(country, target_lang) for country in data["geo_countries"]
        ]

    # Copiar datos numéricos sin traducir
    for key in [
        "wf_counts",
        "geo_counts",
        "timeline_years",
        "timeline_counts",
        "drilldown_data",
    ]:
        if key in data:
            translated_data[key] = data[key]

    # Traducir historias
    if "stories" in data:
        translated_stories = []
        for story in data["stories"]:
            translated_story = story.copy()
            # Traducir campos de texto de la historia
            for field in [
                "title",
                "summary",
                "motive",
                "travel_duration",
                "return_plans",
                "destination_city",
                "destination_country",
            ]:
                if field in story and story[field]:
                    translated_story[field] = translate_text(story[field], target_lang)

            # Traducir menciones
            if "mentions" in story and story["mentions"]:
                translated_story["mentions"] = [
                    translate_text(m, target_lang) for m in story["mentions"] if m
                ]

            # Traducir métodos de viaje
            if "methods" in story and story["methods"]:
                translated_story["methods"] = [
                    translate_text(m, target_lang) for m in story["methods"] if m
                ]

            translated_stories.append(translated_story)

        translated_data["stories"] = translated_stories

    return translated_data


# --- File handling settings ---
from werkzeug.utils import secure_filename

UPLOAD_TEXT_FOLDER = "./multimedia/text"
UPLOAD_IMAGE_FOLDER = "./multimedia/images"
ALLOWED_TEXT_EXTENSIONS = {"txt", "csv"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_TEXT_FOLDER"] = UPLOAD_TEXT_FOLDER
app.config["UPLOAD_IMAGE_FOLDER"] = UPLOAD_IMAGE_FOLDER


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


# --- Delete file endpoint ---
@app.route("/delete-file", methods=["POST"])
def delete_file():
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    rel_path = request.form.get("file_path")
    full_path = os.path.join("multimedia", rel_path)

    try:
        os.remove(full_path)
        flash(f"Deleted {rel_path}", "success")
    except FileNotFoundError:
        flash(f"File not found: {rel_path}", "warning")
    except Exception as e:
        flash(f"Error deleting {rel_path}: {e}", "danger")

    return redirect(url_for("upload_tool"))


# --- Replace file endpoint ---
@app.route("/replace-file", methods=["POST"])
def replace_file():
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    orig_path = request.form.get("orig_path")
    new_file = request.files.get("new_file")

    if not new_file or new_file.filename == "":
        flash("No replacement file selected.", "warning")
        return redirect(url_for("upload_tool"))

    full_orig = os.path.join("multimedia", orig_path)
    try:
        new_file.save(full_orig)
        flash(f"Replaced {orig_path}", "success")
    except Exception as e:
        flash(f"Error replacing {orig_path}: {e}", "danger")

    return redirect(url_for("upload_tool"))


# --- Database connection settings ---
DB_NAME = "house_of_emigrants"
DB_USER = "postgres"
DB_PASS = "666"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_db_connection():
    return psycopg.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )


# --- Routes ---
@app.route("/")
def homepage():
    # Obtener el idioma actual
    current_lang = get_current_language()

    # Usar la interfaz correcta basada en el dispositivo
    if is_touch_device():
        template = "touch-index.html"
    else:
        template = "index.html"  # Crear versión desktop si no existe

    return render_template(template, languages=LANGUAGES, current_lang=current_lang)


@app.route("/login", methods=["GET", "POST"])
def login():
    current_lang = get_current_language()

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()

        query = sql.SQL("SELECT id_admin, email, password FROM admins WHERE email = %s")
        cur.execute(query, (email,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and admin[2] == password:
            session["admin_id"] = admin[0]
            session["admin_email"] = admin[1]
            flash("Login successful!", "success")
            return redirect(url_for("homepage"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login.html", languages=LANGUAGES, current_lang=current_lang)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("homepage"))


@app.route("/changePassword")
def change_password():
    current_lang = get_current_language()
    return render_template(
        "changePassword.html", languages=LANGUAGES, current_lang=current_lang
    )


@app.route("/dataExploration")
def data_exploration():
    # Obtener el idioma actual
    current_lang = get_current_language()

    # Datos de ejemplo para evitar la consulta a la base de datos
    # Esto evita el error de función PostgreSQL no existente

    # Ejemplo de datos para timeline
    timeline_years = [2010, 2011, 2012, 2013, 2014, 2015]
    timeline_counts = [15, 22, 18, 25, 30, 28]

    # Ejemplo de datos para drilldown
    drilldown_data = {
        2010: [
            {"name": "Enero", "y": 2},
            {"name": "Febrero", "y": 1},
            {"name": "Marzo", "y": 3},
            {"name": "Abril", "y": 1},
            {"name": "Mayo", "y": 0},
            {"name": "Junio", "y": 2},
            {"name": "Julio", "y": 1},
            {"name": "Agosto", "y": 0},
            {"name": "Septiembre", "y": 2},
            {"name": "Octubre", "y": 1},
            {"name": "Noviembre", "y": 1},
            {"name": "Diciembre", "y": 1},
        ],
        2011: [
            {"name": "Enero", "y": 1},
            {"name": "Febrero", "y": 2},
            {"name": "Marzo", "y": 2},
            {"name": "Abril", "y": 3},
            {"name": "Mayo", "y": 2},
            {"name": "Junio", "y": 1},
            {"name": "Julio", "y": 3},
            {"name": "Agosto", "y": 2},
            {"name": "Septiembre", "y": 1},
            {"name": "Octubre", "y": 2},
            {"name": "Noviembre", "y": 2},
            {"name": "Diciembre", "y": 1},
        ],
    }

    # Ejemplo de datos para palabras frecuentes (versión en inglés)
    wf_words_en = [
        "Work",
        "Family",
        "Hope",
        "Journey",
        "Future",
        "Freedom",
        "Opportunity",
        "America",
        "Dream",
        "Letters",
    ]
    wf_counts = [45, 38, 32, 29, 26, 22, 18, 15, 12, 10]

    # Ejemplo de datos para distribución geográfica (versión en inglés)
    geo_countries_en = ["United States", "Canada", "Australia", "Brazil", "Argentina"]
    geo_counts = [45, 25, 15, 10, 5]

    # Ejemplo de historias (versión en inglés)
    stories_en = [
        {
            "title": "Gustaf Johansson's Journey",
            "summary": "Story of a young farmer who emigrated to Chicago in 1882.",
            "main_first": "Gustaf",
            "main_last": "Johansson",
            "sex": "male",
            "marital_status": "single",
            "education_level": "basic",
            "legal_status": "documented",
            "mentions": ["Maria Johansson", "Erik Svensson"],
            "departure_date": None,
            "destination_city": "Chicago",
            "destination_country": "United States",
            "motive": "work",
            "travel_duration": "3 months",
            "return_plans": "No",
            "methods": ["steamship", "train"],
        },
        {
            "title": "The Lindberg Sisters",
            "summary": "Three sisters who emigrated together to Minnesota to reunite with their uncle in 1895.",
            "main_first": "Astrid",
            "main_last": "Lindberg",
            "sex": "female",
            "marital_status": "single",
            "education_level": "medium",
            "legal_status": "documented",
            "mentions": ["Ingrid Lindberg", "Helga Lindberg", "Karl Lindberg"],
            "departure_date": None,
            "destination_city": "Saint Paul",
            "destination_country": "United States",
            "motive": "family reunion",
            "travel_duration": "2 months",
            "return_plans": "No",
            "methods": ["steamship", "train"],
        },
        {
            "title": "Olof Larsson's American Dream",
            "summary": "A carpenter who emigrated to Boston looking for better work and fortune in 1878.",
            "main_first": "Olof",
            "main_last": "Larsson",
            "sex": "male",
            "marital_status": "married",
            "education_level": "medium",
            "legal_status": "documented",
            "mentions": ["Elsa Larsson", "Karl Nilsson"],
            "departure_date": None,
            "destination_city": "Boston",
            "destination_country": "United States",
            "motive": "economic",
            "travel_duration": "45 days",
            "return_plans": "After 5 years",
            "methods": ["steamship", "wagon or cart"],
        },
    ]

    # Preparar los datos según el idioma seleccionado
    if current_lang == "es":
        # Versión en español (ya traducida estáticamente para estos ejemplos)
        wf_words = [
            "Trabajo",
            "Familia",
            "Esperanza",
            "Viaje",
            "Futuro",
            "Libertad",
            "Oportunidad",
            "América",
            "Sueño",
            "Cartas",
        ]
        geo_countries = ["Estados Unidos", "Canadá", "Australia", "Brasil", "Argentina"]
        stories = [
            {
                "title": "El viaje de Gustaf Johansson",
                "summary": "Historia de un joven granjero que emigró a Chicago en 1882.",
                "main_first": "Gustaf",
                "main_last": "Johansson",
                "sex": "male",
                "marital_status": "single",
                "education_level": "basic",
                "legal_status": "documented",
                "mentions": ["Maria Johansson", "Erik Svensson"],
                "departure_date": None,
                "destination_city": "Chicago",
                "destination_country": "Estados Unidos",
                "motive": "trabajo",
                "travel_duration": "3 meses",
                "return_plans": "No",
                "methods": ["barco de vapor", "tren"],
            },
            {
                "title": "Las hermanas Lindberg",
                "summary": "Tres hermanas que emigraron juntas a Minnesota para reunirse con su tío en 1895.",
                "main_first": "Astrid",
                "main_last": "Lindberg",
                "sex": "female",
                "marital_status": "single",
                "education_level": "medium",
                "legal_status": "documented",
                "mentions": ["Ingrid Lindberg", "Helga Lindberg", "Karl Lindberg"],
                "departure_date": None,
                "destination_city": "Saint Paul",
                "destination_country": "Estados Unidos",
                "motive": "reunión familiar",
                "travel_duration": "2 meses",
                "return_plans": "No",
                "methods": ["barco de vapor", "tren"],
            },
            {
                "title": "El sueño americano de Olof Larsson",
                "summary": "Un carpintero que emigró a Boston en busca de mejor trabajo y fortuna en 1878.",
                "main_first": "Olof",
                "main_last": "Larsson",
                "sex": "male",
                "marital_status": "married",
                "education_level": "medium",
                "legal_status": "documented",
                "mentions": ["Elsa Larsson", "Karl Nilsson"],
                "departure_date": None,
                "destination_city": "Boston",
                "destination_country": "Estados Unidos",
                "motive": "económico",
                "travel_duration": "45 días",
                "return_plans": "Después de 5 años",
                "methods": ["barco de vapor", "carreta"],
            },
        ]
    else:
        # Versión en inglés (idioma predeterminado)
        wf_words = wf_words_en
        geo_countries = geo_countries_en
        stories = stories_en

    # Procesamiento de datos adicionales para nuevos gráficos
    def process_demographics_and_travel_data(stories_data):
        # Análisis demográfico
        sex_data = {}
        marital_data = {}
        education_data = {}

        # Motivos de emigración
        motive_data = {}

        # Métodos de transporte
        transport_data = {}

        for story in stories_data:
            # Procesar sexo
            if story.get("sex"):
                sex = story["sex"]
                sex_data[sex] = sex_data.get(sex, 0) + 1

            # Procesar estado civil
            if story.get("marital_status"):
                marital = story["marital_status"]
                marital_data[marital] = marital_data.get(marital, 0) + 1

            # Procesar nivel educativo
            if story.get("education_level"):
                education = story["education_level"]
                education_data[education] = education_data.get(education, 0) + 1

            # Procesar motivos
            if story.get("motive"):
                motive = story["motive"]
                motive_data[motive] = motive_data.get(motive, 0) + 1

            # Procesar métodos de transporte
            if story.get("methods"):
                for method in story["methods"]:
                    if method:
                        transport_data[method] = transport_data.get(method, 0) + 1

        return {
            "sex": sex_data,
            "marital": marital_data,
            "education": education_data,
            "motives": motive_data,
            "transport": transport_data,
        }

    # Procesar los datos
    processed_data = process_demographics_and_travel_data(stories)

    # Preparar datos para los gráficos
    # Datos demográficos
    sex_labels = list(processed_data["sex"].keys())
    sex_values = list(processed_data["sex"].values())

    marital_labels = list(processed_data["marital"].keys())
    marital_values = list(processed_data["marital"].values())

    education_labels = list(processed_data["education"].keys())
    education_values = list(processed_data["education"].values())

    # Datos de motivos
    motive_labels = list(processed_data["motives"].keys())
    motive_values = list(processed_data["motives"].values())

    # Datos de transporte
    transport_labels = list(processed_data["transport"].keys())
    transport_values = list(processed_data["transport"].values())

    # Usar la interfaz correcta basada en el dispositivo
    if is_touch_device():
        template = "touch-dataExploration.html"
    else:
        template = "dataExploration.html"  # Versión desktop

    return render_template(
        template,
        timeline_years=json.dumps(timeline_years),
        timeline_counts=json.dumps(timeline_counts),
        drilldown_data=json.dumps(drilldown_data),
        wf_words=json.dumps(wf_words),
        wf_counts=json.dumps(wf_counts),
        geo_countries=json.dumps(geo_countries),
        geo_counts=json.dumps(geo_counts),
        stories=stories,
        # Nuevos datos para gráficos adicionales
        sex_labels=json.dumps(sex_labels),
        sex_values=json.dumps(sex_values),
        marital_labels=json.dumps(marital_labels),
        marital_values=json.dumps(marital_values),
        education_labels=json.dumps(education_labels),
        education_values=json.dumps(education_values),
        motive_labels=json.dumps(motive_labels),
        motive_values=json.dumps(motive_values),
        transport_labels=json.dumps(transport_labels),
        transport_values=json.dumps(transport_values),
        # Longitudes para las estadísticas
        geo_countries_count=len(geo_countries),
        timeline_years_count=len(timeline_years),
        transport_methods_count=len(transport_labels),
        languages=LANGUAGES,
        current_lang=current_lang,
    )


@app.route("/about")
def about():
    current_lang = get_current_language()
    return render_template("about.html", languages=LANGUAGES, current_lang=current_lang)


@app.route("/uploadTool")
def upload_tool():
    if "admin_id" not in session:
        flash("Login required to access upload tools.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    # Get list of existing files
    image_files = []
    text_files = []

    try:
        if not os.path.exists(app.config["UPLOAD_IMAGE_FOLDER"]):
            os.makedirs(app.config["UPLOAD_IMAGE_FOLDER"])

        if not os.path.exists(app.config["UPLOAD_TEXT_FOLDER"]):
            os.makedirs(app.config["UPLOAD_TEXT_FOLDER"])

        for fname in os.listdir(app.config["UPLOAD_IMAGE_FOLDER"]):
            if os.path.isfile(
                os.path.join(app.config["UPLOAD_IMAGE_FOLDER"], fname)
            ) and allowed_file(fname, ALLOWED_IMAGE_EXTENSIONS):
                image_files.append(os.path.join("images", fname))

        for fname in os.listdir(app.config["UPLOAD_TEXT_FOLDER"]):
            if os.path.isfile(
                os.path.join(app.config["UPLOAD_TEXT_FOLDER"], fname)
            ) and allowed_file(fname, ALLOWED_TEXT_EXTENSIONS):
                text_files.append(os.path.join("text", fname))
    except Exception as e:
        flash(f"Error accessing files: {e}", "danger")

    return render_template(
        "uploadTool.html",
        image_files=sorted(image_files),
        text_files=sorted(text_files),
        languages=LANGUAGES,
        current_lang=current_lang,
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    if "admin_id" not in session:
        flash("Login required to upload.", "danger")
        return redirect(url_for("login"))

    uploaded_files = request.files.getlist("files")
    upload_type = request.form.get("type")

    if not uploaded_files:
        flash("No file selected!", "warning")
        return redirect(url_for("upload_tool"))

    for file in uploaded_files:
        filename = secure_filename(file.filename)

        if (
            file
            and upload_type == "text"
            and allowed_file(filename, ALLOWED_TEXT_EXTENSIONS)
        ):
            save_path = os.path.join(app.config["UPLOAD_TEXT_FOLDER"], filename)
            file.save(save_path)
            try:
                subprocess.run(["python", "dataExtraction.py", save_path], check=True)
                flash(f"Uploaded and processed text file: {filename}", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Uploaded {filename}, but processing failed: {e}", "warning")

        elif (
            file
            and upload_type == "image"
            and allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS)
        ):
            save_path = os.path.join(app.config["UPLOAD_IMAGE_FOLDER"], filename)
            file.save(save_path)
            flash(f"Uploaded image file: {filename}", "success")

        else:
            flash(f"File '{filename}' not allowed or wrong type.", "danger")

    return redirect(url_for("upload_tool"))


# ===============================
# CRUD OPERATIONS FOR ADMIN
# ===============================


# --- STORIES MANAGEMENT CRUD ---
@app.route("/admin/stories")
def admin_stories():
    if "admin_id" not in session:
        flash("Login required to access admin panel.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener todas las historias
        cur.execute(
            """
            SELECT id, title, summary, main_first, main_last, sex, marital_status, 
                   education_level, destination_city, destination_country, motive, 
                   travel_duration, return_plans, created_at
            FROM emigrant_stories 
            ORDER BY created_at DESC
        """
        )
        stories = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "admin_stories.html",
            stories=stories,
            languages=LANGUAGES,
            current_lang=current_lang,
        )
    except Exception as e:
        flash(f"Error loading stories: {e}", "danger")
        return redirect(url_for("homepage"))


@app.route("/admin/stories/create", methods=["GET", "POST"])
def admin_create_story():
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Insertar nueva historia
            cur.execute(
                """
                INSERT INTO emigrant_stories 
                (title, summary, main_first, main_last, sex, marital_status, 
                 education_level, destination_city, destination_country, motive, 
                 travel_duration, return_plans)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    request.form["title"],
                    request.form["summary"],
                    request.form["main_first"],
                    request.form["main_last"],
                    request.form["sex"],
                    request.form["marital_status"],
                    request.form["education_level"],
                    request.form["destination_city"],
                    request.form["destination_country"],
                    request.form["motive"],
                    request.form["travel_duration"],
                    request.form["return_plans"],
                ),
            )

            conn.commit()
            cur.close()
            conn.close()

            flash("Story created successfully!", "success")
            return redirect(url_for("admin_stories"))

        except Exception as e:
            flash(f"Error creating story: {e}", "danger")

    return render_template(
        "admin_story_form.html",
        action="create",
        languages=LANGUAGES,
        current_lang=current_lang,
    )


@app.route("/admin/stories/edit/<int:story_id>", methods=["GET", "POST"])
def admin_edit_story(story_id):
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Actualizar historia
            cur.execute(
                """
                UPDATE emigrant_stories 
                SET title=%s, summary=%s, main_first=%s, main_last=%s, sex=%s, 
                    marital_status=%s, education_level=%s, destination_city=%s, 
                    destination_country=%s, motive=%s, travel_duration=%s, return_plans=%s
                WHERE id=%s
            """,
                (
                    request.form["title"],
                    request.form["summary"],
                    request.form["main_first"],
                    request.form["main_last"],
                    request.form["sex"],
                    request.form["marital_status"],
                    request.form["education_level"],
                    request.form["destination_city"],
                    request.form["destination_country"],
                    request.form["motive"],
                    request.form["travel_duration"],
                    request.form["return_plans"],
                    story_id,
                ),
            )

            conn.commit()
            cur.close()
            conn.close()

            flash("Story updated successfully!", "success")
            return redirect(url_for("admin_stories"))

        except Exception as e:
            flash(f"Error updating story: {e}", "danger")

    # GET request - obtener datos de la historia
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT title, summary, main_first, main_last, sex, marital_status, 
                   education_level, destination_city, destination_country, motive, 
                   travel_duration, return_plans
            FROM emigrant_stories WHERE id=%s
        """,
            (story_id,),
        )
        story = cur.fetchone()

        cur.close()
        conn.close()

        if not story:
            flash("Story not found.", "danger")
            return redirect(url_for("admin_stories"))

        return render_template(
            "admin_story_form.html",
            action="edit",
            story_id=story_id,
            story=story,
            languages=LANGUAGES,
            current_lang=current_lang,
        )

    except Exception as e:
        flash(f"Error loading story: {e}", "danger")
        return redirect(url_for("admin_stories"))


@app.route("/admin/stories/delete/<int:story_id>", methods=["POST"])
def admin_delete_story(story_id):
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Eliminar historia
        cur.execute("DELETE FROM emigrant_stories WHERE id=%s", (story_id,))

        if cur.rowcount > 0:
            conn.commit()
            flash("Story deleted successfully!", "success")
        else:
            flash("Story not found.", "warning")

        cur.close()
        conn.close()

    except Exception as e:
        flash(f"Error deleting story: {e}", "danger")

    return redirect(url_for("admin_stories"))


# --- ADMINS MANAGEMENT CRUD ---
@app.route("/admin/admins")
def admin_admins():
    if "admin_id" not in session:
        flash("Login required to access admin panel.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener todos los administradores
        cur.execute(
            "SELECT id_admin, email, created_at FROM admins ORDER BY created_at DESC"
        )
        admins = cur.fetchall()

        cur.close()
        conn.close()

        return render_template(
            "admin_admins.html",
            admins=admins,
            current_admin_id=session["admin_id"],
            languages=LANGUAGES,
            current_lang=current_lang,
        )
    except Exception as e:
        flash(f"Error loading admins: {e}", "danger")
        # En lugar de redirigir a homepage, renderizar template con lista vacía
        return render_template(
            "admin_admins.html",
            admins=[],
            current_admin_id=session.get("admin_id"),
            languages=LANGUAGES,
            current_lang=current_lang,
        )


@app.route("/admin/admins/create", methods=["GET", "POST"])
def admin_create_admin():
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            email = request.form["email"].strip().lower()
            password = request.form["password"]

            # Verificar si el email ya existe
            cur.execute("SELECT id_admin FROM admins WHERE email=%s", (email,))
            if cur.fetchone():
                flash("Email already exists!", "danger")
                return render_template(
                    "admin_admin_form.html",
                    action="create",
                    languages=LANGUAGES,
                    current_lang=current_lang,
                )

            # Insertar nuevo administrador
            cur.execute(
                "INSERT INTO admins (email, password) VALUES (%s, %s)",
                (email, password),
            )

            conn.commit()
            cur.close()
            conn.close()

            flash("Admin created successfully!", "success")
            return redirect(url_for("admin_admins"))

        except Exception as e:
            flash(f"Error creating admin: {e}", "danger")

    return render_template(
        "admin_admin_form.html",
        action="create",
        languages=LANGUAGES,
        current_lang=current_lang,
    )


@app.route("/admin/admins/edit/<int:admin_id>", methods=["GET", "POST"])
def admin_edit_admin(admin_id):
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    current_lang = get_current_language()

    if request.method == "POST":
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            email = request.form["email"].strip().lower()
            password = request.form["password"]

            # Verificar si el email ya existe (excepto el actual)
            cur.execute(
                "SELECT id_admin FROM admins WHERE email=%s AND id_admin!=%s",
                (email, admin_id),
            )
            if cur.fetchone():
                flash("Email already exists!", "danger")
                return redirect(url_for("admin_edit_admin", admin_id=admin_id))

            # Actualizar administrador
            if password:
                cur.execute(
                    "UPDATE admins SET email=%s, password=%s WHERE id_admin=%s",
                    (email, password, admin_id),
                )
            else:
                cur.execute(
                    "UPDATE admins SET email=%s WHERE id_admin=%s", (email, admin_id)
                )

            conn.commit()
            cur.close()
            conn.close()

            flash("Admin updated successfully!", "success")
            return redirect(url_for("admin_admins"))

        except Exception as e:
            flash(f"Error updating admin: {e}", "danger")

    # GET request - obtener datos del administrador
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT email FROM admins WHERE id_admin=%s", (admin_id,))
        admin = cur.fetchone()

        cur.close()
        conn.close()

        if not admin:
            flash("Admin not found.", "danger")
            return redirect(url_for("admin_admins"))

        return render_template(
            "admin_admin_form.html",
            action="edit",
            admin_id=admin_id,
            admin=admin,
            languages=LANGUAGES,
            current_lang=current_lang,
        )

    except Exception as e:
        flash(f"Error loading admin: {e}", "danger")
        return redirect(url_for("admin_admins"))


@app.route("/admin/admins/delete/<int:admin_id>", methods=["POST"])
def admin_delete_admin(admin_id):
    if "admin_id" not in session:
        flash("Login required.", "danger")
        return redirect(url_for("login"))

    # Prevenir que el admin se elimine a sí mismo
    if admin_id == session["admin_id"]:
        flash("You cannot delete your own account!", "danger")
        return redirect(url_for("admin_admins"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Eliminar administrador
        cur.execute("DELETE FROM admins WHERE id_admin=%s", (admin_id,))

        if cur.rowcount > 0:
            conn.commit()
            flash("Admin deleted successfully!", "success")
        else:
            flash("Admin not found.", "warning")

        cur.close()
        conn.close()

    except Exception as e:
        flash(f"Error deleting admin: {e}", "danger")

    return redirect(url_for("admin_admins"))


@app.route("/touch")
def touch_mode():
    session["force_touch"] = True
    return redirect(request.referrer or url_for("homepage"))


@app.route("/desktop")
def desktop_mode():
    # Permitir cambio a modo escritorio
    session.pop("force_touch", None)
    return redirect(request.referrer or url_for("homepage"))


# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
