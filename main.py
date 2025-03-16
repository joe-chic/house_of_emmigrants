from flask import Flask, render_template, request, redirect, url_for, flash
# import psycopg

app = Flask(__name__)

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
    return render_template('dataExploration.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/uploadTool')
def upload_tool():
    return render_template('uploadTool.html')


if __name__ == '__main__':
    app.run(debug=True)
