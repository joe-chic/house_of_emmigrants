from flask import Flask, render_template, request, redirect, url_for, psycopg, flash, jsonify, abort

app = Flask(__name__)

DB_HOST = "localhost"
DB_NAME = "db"
DB_USER = "prueba"
DB_PASSWORD = "666"

def get_db_connection(): # W: Missing function or method docstring
     return psycopg.connect(
         host=DB_HOST,
         dbname=DB_NAME,
         user=DB_USER,
         password=DB_PASSWORD
     )

print("Conexión a Postgres realizada con éxito")

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/changePassword')
def change_password():
    return render_template('changePassword.html')

@app.route('/dataExploration')
def data_exploration():
    """Fetches words from the database and returns them in Highcharts format."""
    conn = get_db_connection()
    if conn is None:
        # Abort with a 500 error if DB connection failed
        abort(500, description="Database connection failed")

    try:
        with conn.cursor() as cur:
            cursor.execute("SELECT palabra FROM Palabras_Clave;")
            words = cur.fetchall() # Returns a list of tuples, e.g., [('word1',), ('word2',)]

        highcharts_data = [{'name': word[0], 'weight': 1} for word in words]

        return jsonify(highcharts_data)

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error fetching data: {error}")
        abort(500, description="Error fetching data from database") # Internal Server Error
    finally:
        if conn:
            conn.close() # Ensure the connection is always closed

    return render_template('dataExploration.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/uploadTool')
def upload_tool():
    return render_template('uploadTool.html')


if __name__ == '__main__':
    app.run(debug=True)
