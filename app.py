from flask import Flask, render_template, request, redirect, session, flash, url_for
from functools import wraps
from flask_session import Session
import sqlite3
import requests
import hashlib
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from os import access
from datetime import datetime, timedelta
import time
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration
import math
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
connection = sqlite3.connect("track_me_run.db")
cursor = connection.cursor()


account = {}
coordinates = []
velocity = []
total_distance = 0
max_velocity = 0
average_velocity = 0


def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon1_rad - lon1_rad

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * \
        math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in kilometers
    distance_km = R * c
    # Convert distance to meters
    distance_m = distance_km * 1000
    return distance_m


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


# def apology(message, code=400):
#     """Render message as an apology to user."""

#     def escape(s):
#         """
#         Escape special characters.

#         https://github.com/jacebrowning/memegen#special-characters
#         """
#         for old, new in [
#             ("-", "--"),
#             (" ", "-"),
#             ("_", "__"),
#             ("?", "~q"),
#             ("%", "~p"),
#             ("#", "~h"),
#             ("/", "~s"),
#             ('"', "''"),
#         ]:
#             s = s.replace(old, new)
#         return s

#     return render_template("apology.html", top=code, bottom=escape(message)), code

# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()

running_sessions = [
    {'datetime': '18/06/2024', 'duration': '23', 'distance': 5,
     'avg': '1.2', 'max': '2', 'calories': 300},
    {'datetime': '18/06/2024', 'duration': '32432',
     'distance': 10, 'avg': '3.4', 'max': '4', 'calories': 600},
    {'datetime': '18/06/2024', 'duration': '485935',
     'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    {'datetime': '18/06/2024', 'duration': '485935',
     'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    {'datetime': '18/06/2024', 'duration': '485935',
     'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    {'datetime': '18/06/2024', 'duration': '485935',
     'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    {'datetime': '18/06/2024', 'duration': '485935',
     'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
]


@app.route("/")
@login_required
def home():

    return render_template("home.html", sessions=running_sessions)


@app.route("/login", methods=["POST", "GET"])
def login():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    session.clear()
    if request.method == "POST":
        check_login = False
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
        if username != n or password != p:
            check_login = True
            return render_template("login.html", check_login=check_login)
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
        check_signup = False
        username = request.form.get("username")
        password = request.form.get("password")
        # Check if the username is already taken
        rows = cursor.execute("SELECT username FROM users")
        for row in rows:
            if username == row[0]:
                check_signup = True
                return render_template("signup.html", check_signup=check_signup)

        # Hash the password before storing
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?,?)", (username, password,))
        connection.commit()
        rows = cursor.execute(
            "SELECT * FROM users WHERE username = ?", (username,))
        session["user_id"] = [row[0] for row in rows][0]
        connection.close()
        return redirect("/")
    else:
        connection.close()
        return render_template("signup.html")


@app.route("/changepass", methods=['GET', 'POST'])
@login_required
def changepass():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    if request.method == "POST":
        check = False
        confirm_check = False
        old_password = request.form.get("old_password")
        rows = cursor.execute(
            "SELECT password FROM users WHERE id = ?", (session['user_id'],))
        for row in rows:
            if old_password != row[0]:
                check = True
                # render lai html voi dong "Your submission is incorrect"
                return render_template("changepass.html", check=check)
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            confirm_check = True
            # render lai html voi dong "Wrong password resubmission"
            return render_template("changepass.html", confirm_check=confirm_check)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?",
                       (new_password, session['user_id'],))
        connection.commit()
        connection.close()
        return redirect("/")
    else:
        connection.close()
        return render_template("changepass.html")
# TO BE CONTINUED


@app.route("/viewprofile")
@login_required
def viewprofile():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    rows = cursor.execute(
        "SELECT * FROM users WHERE id = ?", (session['user_id'],))
    name = 0
    weight = 0
    height = 0
    age = 0
    gender = 0
    bmr = 0
    for row in rows:
        name = row[1]
        weight = row[4]
        height = row[5]
        age = row[6]
        gender = row[7]
        bmr = row[8]
    return render_template("viewprofile.html", name=name, weight=weight, height=height, age=age, gender=gender, bmr=bmr)


@app.route("/updateprofile", methods=['GET', 'POST'])
@login_required
def updateprofile():
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    rows = cursor.execute(
        "SELECT * FROM users WHERE id = ?", (session['user_id'],))
    cur_name = 0
    cur_weight = 0
    cur_height = 0
    cur_age = 0
    cur_gender = 0
    for row in rows:
        cur_name = row[1]
        cur_weight = row[4]
        cur_height = row[5]
        cur_age = row[6]
        cur_gender = row[7]
    if request.method == "POST":
        name = request.form.get("name")
        if name == "":
            name = cur_name
        try:
            weight = int(request.form.get("weight"))
        except ValueError:
            weight = cur_weight
        try:
            height = int(request.form.get("height"))
        except ValueError:
            height = cur_height
        try:
            age = int(request.form.get("age"))
        except ValueError:
            age = cur_age
        gender = request.form.get("gender")
        if gender == None:
            gender = cur_gender
        if gender == "male":
            bmr = 66 + (6.23 * weight * 2.20462) + \
                (12.7 * height * 0.393701) - (6.8 * age)
        else:
            bmr = 655 + (4.3 * weight * 2.20462) + \
                (4.7 * height * 0.393701) - (4.7 * age)
        cursor.execute("UPDATE users SET name = ?, weight = ?, height = ?, age = ?, gender = ?, bmr = ? WHERE id = ?",
                       (name, weight, height, age, gender, bmr, session['user_id'],))
        connection.commit()
        return redirect("/viewprofile")
    return render_template("updateprofile.html")


@app.route("/startsession")
@login_required
def startsession():
    oauth_client = BackendApplicationClient(
        client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3")
    token_url = "https://api2.arduino.cc/iot/v1/clients/token"
    oauth = OAuth2Session(client=oauth_client)
    token = oauth.fetch_token(
        token_url=token_url,
        client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3",
        client_secret="IzJKMUUnl09D1aTZQoYWxu31PpmKH1JLPPWVMBliDCet0aClF0MWXF5hGnuZH5c7",
        include_client_id=True,
        audience="https://api2.arduino.cc/iot",
    )

    # store access token in access_token variable
    access_token = token.get("access_token")
    # configure and instance the API client with our access_token
    client_config = iot.Configuration(host="https://api2.arduino.cc/iot")
    client_config.access_token = access_token
    api = None
    thing_id = None
    with iot.ApiClient(client_config) as client:
        # Create an instance of the API class
        api = iot.PropertiesV2Api(client)
        thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824"  # iPhone thing
        # thing_id = "a798decb-21e5-4b5f-a659-f4941437ae8f" # test_thing
    # client = iot.ApiClient(client_config)

    # Change this based on the device being used
    # thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824"

    # Custom variables for debugging
    looping = True  # whether the program continuously fetches data in a loop
    minutes_ago = 1  # how far back in time should the program fetch data, more minutes means longer fetch time
    # how many seconds should the program wait before fetching again
    sleep_duration = float(5)

    # init data for Properties API interactions
    # api = iot.PropertiesV2Api(client)
    prev_time_record = datetime.min  # reset prev_time_record

    # Change these property IDs based on info in the Thing setup page
    gps_id = "a058906f-caad-465b-96d3-da1981e81be7"
    gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146"
    acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5"

    property_id = gps_id
    # final output
    max_velocity = 0
    average_velocity = 0
    total_distance = 0
    total_calorie_burnt = 0
    coordinates = []
    velocity = []
    first_fetch = True
    interval_length = 0
    previous_time = 0
    duration = 0
    while (True):
        try:
            now_time = datetime.now()
            if first_fetch == False:
                if now_time.second < previous_time.second:
                    interval_length = now_time.second + 60 + \
                        (now_time.microsecond/1000000) - previous_time.second - \
                        (previous_time.microsecond/1000000)
                else:
                    interval_length = now_time.second + \
                        (now_time.microsecond/1000000) - previous_time.second - \
                        (previous_time.microsecond/1000000)
                # interval length, not finished, datetime type issue
            previous_time = now_time
            print(f"Now:\t{now_time}")
            prev_time = now_time + timedelta(minutes=-minutes_ago)
            print(f"{minutes_ago} mins ago:\t{prev_time}")
            formatted_month = ('00' + str(prev_time.month))[-2:]
            formatted_date = ('00' + str(prev_time.day))[-2:]
            formatted_hour = ('00' + str(prev_time.hour - 7))[-2:]
            formatted_minute = ('00' + str(prev_time.minute))[-2:]
            formatted_second = ('00' + str(prev_time.second))[-2:]
            formatted_time = str(prev_time.year) + '-' + formatted_month + '-' + formatted_date + \
                'T' + formatted_hour + ':' + formatted_minute + ':' + formatted_second + 'Z'
            print(f"Formatted:\t{formatted_time}")

            # resp = api.properties_v2_list(thing_id)
            resp = api.properties_v2_show(thing_id, gps_id)
            # resp = api.properties_v2_timeseries(thing_id, property_id, desc=True, _from=formatted_time, interval=1)
            # if (len(resp.data) > 0):
            # 	print(f"Batch size: {len(resp.data)}")
            # 	if (resp.data[0].time != prev_time_record):
            # 		prev_time_record = resp.data[0].time
            # 		print(resp.data[0])
            # 	else:
            # 		print("No new records since last fetch")
            # else:
            # 	print(f"No records in last {minutes_ago} minutes")
            # print(resp)
            print(f"{resp.value_updated_at}\tGyroscope_X: {resp.last_value}")
            coordinates.append(
                tuple((resp._last_value['lat'], resp._last_value['lon'])))
            if first_fetch == True:
                first_fetch = False
            else:
                distance = haversine(coordinates[len(coordinates)-2][0], coordinates[len(
                    coordinates)-2][1], coordinates[len(coordinates)-1][0], coordinates[len(coordinates)-1][0])
                total_distance += distance
                current_velocity = distance / interval_length
                duration += interval_length
                max_velocity = max(max_velocity, current_velocity)
                velocity.append(current_velocity)
                print(current_velocity)
                print(distance)
                print(interval_length)
        except ApiException as e:
            print("Got an exception: {}".format(e))
        if len(velocity) >= 3:
            if coordinates[-1] == coordinates[-2] and coordinates[-2] == coordinates[-3]:
                summ = 0
                for i in range(0, len(velocity)-2):
                    summ += i
                average_velocity = summ / len(velocity)
                session_dict = {
                    'datetime': "25/06/2024",
                    'duration': duration - 15,
                    'distance': total_distance,
                    'avg': average_velocity,
                    'max': max_velocity,
                    'calories': 1000
                }
                running_sessions.append(session_dict)
                return redirect("/")
        print()
        time.sleep(sleep_duration)


@app.route("/finishsession")
@login_required
def finishsession():
    return


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect(url_for("login"))
