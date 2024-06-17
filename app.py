from flask import Flask, render_template, request, redirect, session, flash, url_for
from functools import wraps
from flask_session import Session
import sqlite3
import requests
import hashlib 


app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
connection = sqlite3.connect("track_me_run.db")
cursor = connection.cursor()

account = {}
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()

@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Check if the username exists in the account dictionary
        rows = cursor.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        )
        n = 0
        p = 0
        i = 0
        for row in rows:
            n = row[2]
            p = row[3]
            i = row[0]
        if username != n or  password != p:
            return apology("Incorrect username or password")
        session["user_id"] = i
        connection.close()
        return redirect("/")
    else:
        connection.close()
        return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    session.clear()
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Check if the username is already taken
        rows = cursor.execute("SELECT username FROM users")
        for row in rows:
            if username == row[0]:
                return apology("Username already exists")        
        
        # Hash the password before storing
        cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", (username,password,))
        connection.commit()
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        session["user_id"] = [row[0] for row in rows][0]
        connection.close()
        return redirect("/")
    else:
        connection.close()
        return render_template("signup.html")

@app.route("/changepass",methods=['GET','POST'])
@login_required
def changepass():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    if request.method == "POST":
        check = False
        confirm_check = False
        old_password = request.form.get("old_password")
        rows = cursor.execute("SELECT password FROM users WHERE id = ?",(session['user_id'],))
        for row in rows:
            if old_password != row[0]:
                check = True
                return render_template("changepass.html", check = check) #render lai html voi dong "Your submission is incorrect"
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            confirm_check = True
            return render_template("changepass.html", confirm_check = confirm_check) #render lai html voi dong "Wrong password resubmission"
        cursor.execute("UPDATE users SET password = ? WHERE id = ?",(new_password,session['user_id'],))
        connection.commit()
        connection.close()
        return redirect("/")
    else:
        connection.close()
        return render_template("changepass.html")
# TO BE CONTINUED
@app.route("/checkprofile",methods=['GET','POST'])
@login_required
def checkprofile():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    if request.method == "POST":
        name = request.form.get("name")
        weight = int(request.form.get("weight"))
        height = int(request.form.get("height"))
        age = int(request.form.get("age"))
        gender = request.form.get("gender")
        if gender == "male":
            bmr = 66 + (6.23 * weight * 2.20462) + (12.7 * height *0.393701) - (6.8 * age)
        else:
            bmr = 655 + (4.3 * weight * 2.20462) + (4.7 * height *0.393701) - (4.7 * age)
        cursor.execute("UPDATE users SET name = ?, weight = ?, height = ?, age = ?, gender = ?, bmr = ? WHERE id = ?",(name, weight, height, age, gender,bmr,session['user_id'],))
        connection.commit()
        return redirect("/")
    rows = cursor.execute("SELECT name FROM users WHERE id = ?",(session['user_id'],))
    return render_template("checkprofile.html")
@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect(url_for("login"))




    
