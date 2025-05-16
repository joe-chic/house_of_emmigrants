from flask import Flask, render_template, request, redirect, url_for, flash, session
from psycopg import sql
import psycopg
import os
import json
import subprocess

app = Flask(__name__)
app.secret_key = 'a12f9c2b4d5e6f7g8h9i0jklmnopqrst'  # Needed for flashing messages

from flask import send_from_directory
@app.route('/multimedia/<path:filename>')
def serve_multimedia(filename):
    return send_from_directory('multimedia', filename)

# FILES handlings
from werkzeug.utils import secure_filename
UPLOAD_TEXT_FOLDER = '.\\multimedia\\text'
UPLOAD_IMAGE_FOLDER = '.\\multimedia\\images'
ALLOWED_TEXT_EXTENSIONS = {'txt', 'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_TEXT_FOLDER'] = UPLOAD_TEXT_FOLDER
app.config['UPLOAD_IMAGE_FOLDER'] = UPLOAD_IMAGE_FOLDER

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/delete-file', methods=['POST'])
def delete_file():
    # require login
    if 'admin_id' not in session:
        flash('Login required.', 'danger')
        return redirect(url_for('login'))

    # path is like "text/filename.txt" or "images/photo.png"
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

    # overwrite the original
    full_orig = os.path.join('multimedia', orig_path)
    try:
        # optional: check extension matches orig_path’s extension
        new_file.save(full_orig)
        flash(f"Replaced {orig_path}", 'success')
    except Exception as e:
        flash(f"Error replacing {orig_path}: {e}", 'danger')

    return redirect(url_for('upload_tool'))

# Database connection settings
DB_NAME = 'house_of_emigrants'
DB_USER = 'postgres'
DB_PASS = '666'
DB_HOST = 'localhost'
DB_PORT = '5432'

def get_db_connection():
    conn = psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    return conn

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        print(email, " ", password)
        conn = get_db_connection()
        cur = conn.cursor()

        # TODO: Make it work so that autofill is not a problem.
        
        query = sql.SQL("SELECT * FROM admins WHERE email = %s")
        cur.execute(query, (email.lower(),))
        conn.commit()
        admin = cur.fetchone()
        print(admin)
        
        cur.close()
        conn.close()

        # admin[2] = password (plaintext now)
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
    cur = conn.cursor()

    # 1) Timeline: count of relatos per year
    cur.execute("""
    SELECT
        EXTRACT(YEAR FROM fecha_relato)::INT AS year,
        COUNT(*) AS total
    FROM relatos_emigracion
    GROUP BY year
    ORDER BY year;
    """)
    timeline = cur.fetchall()

    # 2) Word frequency: top 10 palabras by total frecuencia
    cur.execute("""
      SELECT pk.palabra, SUM(rp.frecuencia) AS freq
      FROM Relatos_Palabras rp
      JOIN Palabras_Clave pk ON rp.palabra_clave_id = pk.palabra_clave_id
      GROUP BY pk.palabra
      ORDER BY freq DESC;
    """)
    word_freq = cur.fetchall()  # [('migrar', 50), ('trabajo', 42), ...]

    # 3) Geographic distribution: count personas by country
    cur.execute("""
      SELECT pais_origen, COUNT(*) AS cnt
      FROM Personas
      GROUP BY pais_origen
      ORDER BY cnt DESC;
    """)
    geo = cur.fetchall()  # [('Sweden', 100), ('Mexico', 80), ...]

    # 4) Recent stories: pull last 3 relatos with person info
    cur.execute("""
      SELECT r.titulo_relato, r.fecha_relato, p.nombre, p.apellido
      FROM Relatos_Emigracion r
      JOIN Personas p ON r.persona_id = p.persona_id
      ORDER BY r.fecha_relato DESC;
    """)
    stories = cur.fetchall()  # [('Title1', date1, 'Jane', 'Doe'), ...]

    cur.close()
    conn.close()

    # Turn into JSON-friendly structures
    timeline_years, timeline_counts = zip(*timeline) if timeline else ([], [])
    wf_words, wf_counts           = zip(*word_freq) if word_freq else ([], [])
    geo_countries, geo_counts     = zip(*geo) if geo else ([], [])

    return render_template('dataExploration.html',
        timeline_years   = json.dumps(list(timeline_years)),
        timeline_counts  = json.dumps(list(timeline_counts)),
        wf_words         = json.dumps(list(wf_words)),
        wf_counts        = json.dumps(list(wf_counts)),
        geo_countries    = json.dumps(list(geo_countries)),
        geo_counts       = json.dumps(list(geo_counts)),
        stories          = stories
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
    # Text files
    for fname in os.listdir(app.config['UPLOAD_TEXT_FOLDER']):
        files.append({
            'name': fname,
            'type': 'text',
            'path': f'text/{fname}'
        })
    # Image files
    for fname in os.listdir(app.config['UPLOAD_IMAGE_FOLDER']):
        files.append({
            'name': fname,
            'type': 'image',
            'path': f'images/{fname}'
        })
    return render_template('uploadTool.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'admin_id' not in session:
        flash('Login required to upload.', 'danger')
        return redirect(url_for('login'))

    uploaded_files = request.files.getlist('files')
    upload_type    = request.form.get('type')  # 'text' or 'image'

    if not uploaded_files:
        flash('No file selected!', 'warning')
        return redirect(url_for('upload_tool'))

    for file in uploaded_files:
        filename = secure_filename(file.filename)

        # === TEXT FILES ===
        if file and upload_type == 'text' and allowed_file(filename, ALLOWED_TEXT_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_TEXT_FOLDER'], filename)
            file.save(save_path)

            # Immediately invoke your dataExtraction script on that file:
            try:
                # Assumes dataExtraction.py is in the same directory as main.py
                subprocess.run(
                    ['python', 'dataExtraction.py', save_path],
                    check=True,
                )
                flash(f"Uploaded and processed text file: {filename}", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Uploaded {filename}, but processing failed: {e}", "warning")

        # === IMAGE FILES ===
        elif file and upload_type == 'image' and allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename)
            file.save(save_path)
            flash(f"Uploaded image file: {filename}", "success")

        else:
            flash(f"File '{filename}' not allowed or wrong type.", "danger")

    return redirect(url_for('upload_tool'))


if __name__ == '__main__':
    app.run(debug=True)