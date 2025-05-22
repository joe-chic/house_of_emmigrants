from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from psycopg import sql
import psycopg
import os
import json
import subprocess

app = Flask(__name__)
app.secret_key = 'a12f9c2b4d5e6f7g8h9i0jklmnopqrst'  # Needed for flashing messages

# --- Multimedia serving ---
@app.route('/multimedia/<path:filename>')
def serve_multimedia(filename):
    return send_from_directory('multimedia', filename)

# --- File handling settings ---
from werkzeug.utils import secure_filename
UPLOAD_TEXT_FOLDER = './multimedia/text'
UPLOAD_IMAGE_FOLDER = './multimedia/images'
ALLOWED_TEXT_EXTENSIONS = {'txt', 'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_TEXT_FOLDER'] = UPLOAD_TEXT_FOLDER
app.config['UPLOAD_IMAGE_FOLDER'] = UPLOAD_IMAGE_FOLDER

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# --- Delete file endpoint ---
@app.route('/delete-file', methods=['POST'])
def delete_file():
    if 'admin_id' not in session:
        flash('Login required.', 'danger')
        return redirect(url_for('login'))

    rel_path = request.form.get('file_path')
    full_path = os.path.join('multimedia', rel_path)

    try:
        os.remove(full_path)
        flash(f"Deleted {rel_path}", 'success')
    except FileNotFoundError:
        flash(f"File not found: {rel_path}", 'warning')
    except Exception as e:
        flash(f"Error deleting {rel_path}: {e}", 'danger')

    return redirect(url_for('upload_tool'))

# --- Replace file endpoint ---
@app.route('/replace-file', methods=['POST'])
def replace_file():
    if 'admin_id' not in session:
        flash('Login required.', 'danger')
        return redirect(url_for('login'))

    orig_path = request.form.get('orig_path')
    new_file = request.files.get('new_file')

    if not new_file or new_file.filename == '':
        flash('No replacement file selected.', 'warning')
        return redirect(url_for('upload_tool'))

    full_orig = os.path.join('multimedia', orig_path)
    try:
        new_file.save(full_orig)
        flash(f"Replaced {orig_path}", 'success')
    except Exception as e:
        flash(f"Error replacing {orig_path}: {e}", 'danger')

    return redirect(url_for('upload_tool'))

# --- Database connection settings ---
DB_NAME = 'house_of_emigrants'
DB_USER = 'postgres'
DB_PASS = '666'
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

# --- Routes ---
@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()

        query = sql.SQL("SELECT id_admin, email, password FROM admins WHERE email = %s")
        cur.execute(query, (email,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and admin[2] == password:
            session['admin_id'] = admin[0]
            session['admin_email'] = admin[1]
            flash('Login successful!', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('homepage'))

@app.route('/changePassword')
def change_password():
    return render_template('changePassword.html')

@app.route('/dataExploration')
def data_exploration():
    conn = get_db_connection()
    
    # Initialize data structures
    timeline_years, timeline_counts = [], []
    wf_words, wf_counts = [], []
    geo_cities, geo_counts = [], [] # Changed from geo_countries for clarity
    stories_list = [] # Renamed from 'stories' for clarity before processing

    try:
        with conn.cursor() as cur:
            with conn.transaction():
                # 1) Timeline of Emigration Departure Dates
                timeline_cursor_name = "timeline_c_py"
                cur.execute("CALL get_emigration_departure_timeline_proc(%s);", (timeline_cursor_name,))
                cur.execute(sql.SQL("FETCH ALL FROM {};").format(sql.Identifier(timeline_cursor_name)))
                timeline_data = cur.fetchall()
                if timeline_data:
                    timeline_years = [row[0] for row in timeline_data]
                    timeline_counts = [row[1] for row in timeline_data]

                # 2) Top Keywords
                keyword_cursor_name = "keyword_c_py"
                limit_for_keywords = 10
                cur.execute("CALL get_top_salient_keywords_proc(%s, %s);", (keyword_cursor_name, limit_for_keywords))
                cur.execute(sql.SQL("FETCH ALL FROM {};").format(sql.Identifier(keyword_cursor_name)))
                word_freq_data = cur.fetchall()
                if word_freq_data:
                    wf_words = [row[0] for row in word_freq_data]
                    wf_counts = [row[1] for row in word_freq_data]

                # 3) Geographic Distribution (Destination Cities)
                dest_city_cursor_name = "dest_city_c_py"
                cur.execute("CALL get_destination_city_distribution_proc(%s);", (dest_city_cursor_name,))
                cur.execute(sql.SQL("FETCH ALL FROM {};").format(sql.Identifier(dest_city_cursor_name)))
                geo_data = cur.fetchall()
                if geo_data:
                    geo_cities = [row[0] for row in geo_data] # Now city names
                    geo_counts = [row[1] for row in geo_data]

                # 4) Recent Stories with Full Details
                recent_stories_cursor_name = "recent_stories_c_py"
                limit_for_recent_stories = 5 # Or however many you want
                cur.execute("CALL get_recent_stories_details_proc(%s, %s);", (recent_stories_cursor_name, limit_for_recent_stories))
                cur.execute(sql.SQL("FETCH ALL FROM {};").format(sql.Identifier(recent_stories_cursor_name)))
                recent_stories_raw = cur.fetchall()

                if recent_stories_raw:
                    for row in recent_stories_raw:
                        stories_list.append({
                            'title':            row[0],
                            'summary':          row[1],
                            'main_first':       row[2],
                            'main_last':        row[3],
                            'sex':              row[4],
                            'marital_status':   row[5],
                            'education_level':  row[6],
                            'legal_status':     row[7],
                            'mentions':         row[8] or [], # Handled by COALESCE in SQL now
                            'departure_date':   row[9],
                            'destination_city': row[10],
                            'destination_country': row[11],
                            'motive':           row[12],
                            'travel_duration':  row[13],
                            'return_plans':     row[14],
                            'methods':          row[15] or [], # Handled by COALESCE in SQL now
                            'id_text_debug':    str(row[16]) # For debugging or unique key if needed
                        })
            # Transaction commits here
            
    except psycopg.Error as e:
        flash(f"Database error fetching data for exploration: {e}", "danger")
        app.logger.error(f"Data exploration DB error: {e}\nSQLSTATE: {e.sqlstate}")
        # Ensure all lists are empty on error
        timeline_years, timeline_counts = [], []
        wf_words, wf_counts = [], []
        geo_cities, geo_counts = [], []
        stories_list = []
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        app.logger.error(f"Data exploration general error: {e}")
        timeline_years, timeline_counts = [], []
        wf_words, wf_counts = [], []
        geo_cities, geo_counts = [], []
        stories_list = []
    finally:
        if conn:
            conn.close()

    return render_template('dataExploration.html',
        timeline_years   = json.dumps(list(timeline_years)),
        timeline_counts  = json.dumps(list(timeline_counts)),
        wf_words         = json.dumps(list(wf_words)),
        wf_counts        = json.dumps(list(wf_counts)),
        geo_items        = json.dumps(list(geo_cities)), # Changed to geo_items for cities
        geo_item_counts  = json.dumps(list(geo_counts)),
        stories          = stories_list # Pass the processed list of dicts
    )

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/uploadTool')
def upload_tool():
    if 'admin_id' not in session:
        flash('Please log in to access the upload tool.', 'warning')
        return redirect(url_for('login'))

    files = []
    for fname in os.listdir(app.config['UPLOAD_TEXT_FOLDER']):
        files.append({'name': fname, 'type': 'text', 'path': f'text/{fname}'})
    for fname in os.listdir(app.config['UPLOAD_IMAGE_FOLDER']):
        files.append({'name': fname, 'type': 'image', 'path': f'images/{fname}'})
    return render_template('uploadTool.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'admin_id' not in session:
        flash('Login required to upload.', 'danger')
        return redirect(url_for('login'))

    uploaded_files = request.files.getlist('files')
    upload_type    = request.form.get('type')

    if not uploaded_files:
        flash('No file selected!', 'warning')
        return redirect(url_for('upload_tool'))

    for file in uploaded_files:
        filename = secure_filename(file.filename)

        if file and upload_type == 'text' and allowed_file(filename, ALLOWED_TEXT_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_TEXT_FOLDER'], filename)
            file.save(save_path)
            try:
                subprocess.run(['python', 'dataExtraction.py', save_path], check=True)
                flash(f"Uploaded and processed text file: {filename}", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Uploaded {filename}, but processing failed: {e}", "warning")

        elif file and upload_type == 'image' and allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename)
            file.save(save_path)
            flash(f"Uploaded image file: {filename}", "success")

        else:
            flash(f"File '{filename}' not allowed or wrong type.", "danger")

    return redirect(url_for('upload_tool'))

if __name__ == '__main__':
    app.run(debug=True)
