from flask import Flask, render_template, request, redirect, session, flash, url_for
from functools import wraps
from flask_session import Session
import sqlite3
import requests
import hashlib
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from os import access
import os
import threading
from threading import Thread, current_thread, Event
from datetime import datetime, timedelta, timezone
import time
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration
import subprocess
import sys
import arduino_cloud

app = Flask(__name__)

# DONE: if using permanent session, user will be forced to logout after timeout even when still using app
# TODO: save database to a remote server
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
connection = sqlite3.connect("track_me_run.db")
cursor = connection.cursor()
arduino_cloud.session_done.set()
# whether parent thread can add another session record to db, only once per session
can_add_to_db = Event()
can_add_to_db.clear()
account = {}
coordinates = []
velocity = []
total_distance = 0
max_velocity = 0
average_velocity = 0
start_second = 0
goal_distance = 0
goal_calories = 0
goal_flag = False
running_sessions = [
    # {'datetime': '18/06/2024', 'duration': '23', 'distance': 5,
    #  'avg': '1.2', 'max': '2', 'calories': 300},
    # {'datetime': '18/06/2024', 'duration': '32432',
    #  'distance': 10, 'avg': '3.4', 'max': '4', 'calories': 600},
    # {'datetime': '18/06/2024', 'duration': '485935',
    #  'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    # {'datetime': '18/06/2024', 'duration': '485935',
    #  'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    # {'datetime': '18/06/2024', 'duration': '485935',
    #  'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    # {'datetime': '18/06/2024', 'duration': '485935',
    #  'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
    # {'datetime': '18/06/2024', 'duration': '485935',
    #  'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
]


def startsess_helper(running_sessions, weight, start_second):
    arduino_cloud.start_session(running_sessions, weight, start_second)
    print("updated running_sessions")
    # add_sessions_for(session['user_id'], running_sessions=running_sessions)
    # print("added newest session to database")
    # print("done with session")

    # this is when running_sessions and db are not synchronized
    can_add_to_db.set()  # must run before session_done.set()
    print("can_add_to_db now set")
    arduino_cloud.session_done.set()  # must run after everything else here
    # return redirect("/")


def add_sessions_for(user_id, running_sessions):
    # add last session data to database
    # print(running_sessions)
    session_dict = running_sessions[-1]
    print(f"Last item of running_sessions: {session_dict}")
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO sessions (user_id, datetime, duration, distance, avg_speed, max_speed, calories) VALUES (?,?,?,?,?,?,?)",
        (user_id, session_dict['datetime'], session_dict['duration'], session_dict['distance'], session_dict['avg'], session_dict['max'], session_dict['calories']))
    connection.commit()
    connection.close()
    return


def get_sessions_from(user_id) -> list:
    connection = sqlite3.connect("track_me_run.db")
    cursor = connection.cursor()
    # populate running_sessions with data from db
    temp_running_sessions = []
    sesses = cursor.execute(
        "SELECT * FROM sessions WHERE user_id = ?", (session['user_id'],))
    for sess in sesses:
        sess_dict = {
            'datetime': sess[2],
            'duration': sess[3],
            'distance': sess[4],
            'avg': sess[5],
            'max': sess[6],
            'calories': sess[7]
        }
        temp_running_sessions.append(sess_dict)
        # print(temp_running_sessions[-1])

    connection.close()
    return temp_running_sessions


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

# DONE: if a session is in progress, change button to "back to session"


@app.route("/")
@login_required
def home():
    # only retrieve from db if running_sessions and db are synchronized
    session_in_progress = not (
        arduino_cloud.session_done.is_set() and not can_add_to_db.is_set())
    if (not session_in_progress):
        global running_sessions
        running_sessions = get_sessions_from(session['user_id'])
        print("got running_sessions from db")

    # print(f"Last item of running_sessions: {running_sessions[-1]}")
    if (not can_add_to_db.is_set() or len(running_sessions) == 0):
        return render_template("home.html", sessions=reversed(running_sessions), session_in_progress=session_in_progress)
    else:
        # if hasn't saved to db, don't display the lastest session in running_sessions
        return render_template("home.html", sessions=reversed(running_sessions[:-1]), session_in_progress=session_in_progress)

    # TODO: let user delete sessions from the home page


@app.route("/login", methods=["POST", "GET"])
def login():
    session.clear()

    if request.method == "POST":
        connection = sqlite3.connect("track_me_run.db")
        cursor = connection.cursor()
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

        global running_sessions
        running_sessions = get_sessions_from(session['user_id'])
        print("got running_sessions from db")
        return redirect("/")
    else:
        # connection.close()
        return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    session.clear()

    if request.method == "POST":
        connection = sqlite3.connect("track_me_run.db")
        cursor = connection.cursor()
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
        return redirect("/fillprofile")
    else:
        # connection.close()
        return render_template("signup.html")


@app.route("/fillprofile", methods=["POST", "GET"])
@login_required
def fillprofile():
    if request.method == "POST":
        connection = sqlite3.connect("track_me_run.db")
        cursor = connection.cursor()
        name = request.form.get("name")
        weight = float(request.form.get("weight"))
        height = float(request.form.get("height"))
        age = int(request.form.get("age"))
        gender = request.form.get("gender")
        if gender == "male":
            bmr = 66 + (6.23 * weight * 2.20462)
            bmr = bmr + (12.7 * height * 0.393701) - (6.8 * age)
        else:
            bmr = 655 + (4.3 * weight * 2.20462)
            bmr = bmr + (4.7 * height * 0.393701) - (4.7 * age)
        cursor.execute("UPDATE users SET name = ?, weight = ?, height = ?, age = ?, gender = ?, bmr = ? WHERE id = ?",
                       (name, weight, height, age, gender, bmr, session['user_id'],))
        connection.commit()
        connection.close()

        global running_sessions
        running_sessions = get_sessions_from(
            session['user_id'])  # should be empty
        return redirect("/")
    return render_template("fillprofile.html")


@app.route("/changepass", methods=['GET', 'POST'])
@login_required
def changepass():
    if request.method == "POST":
        connection = sqlite3.connect("track_me_run.db")
        cursor = connection.cursor()
        check = False
        confirm_check = False
        old_password = request.form.get("old_password")
        rows = cursor.execute(
            "SELECT password FROM users WHERE id = ?", (session['user_id'],))

        # FIXME: make sure connection is closed if cannot change password
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
        # connection.close()
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
        age = int(row[6])
        gender = row[7]
        bmr = row[8]
    connection.close()
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
        cur_age = int(row[6])
        cur_gender = row[7]
    # DONE: send this data to html page
    connection.close()

    if request.method == "POST":
        connection = sqlite3.connect("track_me_run.db")
        cursor = connection.cursor()
        name = request.form.get("name")
        if name == "":
            name = cur_name
        try:
            weight = float(request.form.get("weight"))
        except ValueError:
            print("weight value error")
            weight = cur_weight
        try:
            height = float(request.form.get("height"))
        except ValueError:
            print("height value error")
            height = cur_height
        try:
            age = int(request.form.get("age"))
        except ValueError:
            print("age value error")
            age = cur_age
        gender = request.form.get(cur_gender)
        if gender == None:
            gender = cur_gender
        if gender == "male":
            bmr = 66 + (6.23 * weight * 2.20462)
            bmr = bmr + (12.7 * height * 0.393701) - (6.8 * age)
        else:
            bmr = 655 + (4.3 * weight * 2.20462)
            bmr = bmr + (4.7 * height * 0.393701) - (4.7 * age)
        cursor.execute("UPDATE users SET name = ?, weight = ?, height = ?, age = ?, gender = ?, bmr = ? WHERE id = ?",
                       (name, weight, height, age, gender, bmr, session['user_id'],))
        connection.commit()
        connection.close()
        return redirect("/viewprofile")
    # connection.close()
    return render_template("updateprofile.html", name=cur_name, weight=cur_weight, height=cur_height, age=cur_age, gender=cur_gender)

# DONE: if a session is in progress, skip setgoal in going to /startsession


@app.route("/setgoal", methods=['GET', 'POST'])
@login_required
def setgoal():
    # if already in a session, redirect straight to /startsession
    if not (arduino_cloud.session_done.is_set() and not can_add_to_db.is_set()):
        return redirect("/startsession")

    if request.method == "POST":
        global goal_distance
        global goal_calories
        global goal_flag  # if goal is set for this session
        goal_distance = request.form.get("distance")
        goal_calories = request.form.get("calories")

        if goal_distance == None or goal_calories == None:
            # if set goal is skipped
            goal_calories = 0
            goal_distance = 0
            goal_flag = False
        else:
            goal_distance = float(goal_distance)
            goal_calories = float(goal_calories)
            goal_flag = True

        return redirect("/startsession")
    return render_template("setgoal.html")


@app.route("/startsession")
@login_required
def startsess():
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
        cur_age = int(row[6])
        cur_gender = row[7]
    connection.close()

    first_time = False
    parent_thread = current_thread()

    if (arduino_cloud.session_done.is_set() and not can_add_to_db.is_set()):
        # allow new session to begin
        arduino_cloud.session_done.clear()  # must run before everything else here
        first_time = True
        global start_second
        start_second = datetime.now(timezone.utc)
        print(
            f"Session begins at {start_second}----------------------------------------------------------------------")
        child_thread = Thread(target=startsess_helper,
                              args=(running_sessions, cur_weight, start_second))
        child_thread.start()  # must run after everything else here

    if (current_thread() == parent_thread):
        now = datetime.now(timezone.utc)
        elapsed = int((now - start_second).total_seconds())
        return render_template("startsession.html", elapsed_time=elapsed, first_time=first_time)

    # print("Session in progress")
    # arduino_cloud.start_session(running_sessions)
    # # clicked = not clicked
    # print("Session finished")
    # while (clicked):
    # 	print("nah")
    # print("stopped")
    # if (clicked):
    # time.sleep(5)
    # result = subprocess.run([sys.executable, "-c", "import time; time.sleep(2); print('print by subprocess')"], capture_output=True, text=True)
    # return redirect("/")


# def startsession():
# 		oauth_client = BackendApplicationClient(
# 				client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3")
# 		token_url = "https://api2.arduino.cc/iot/v1/clients/token"
# 		oauth = OAuth2Session(client=oauth_client)
# 		token = oauth.fetch_token(
# 				token_url=token_url,
# 				client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3",
# 				client_secret="IzJKMUUnl09D1aTZQoYWxu31PpmKH1JLPPWVMBliDCet0aClF0MWXF5hGnuZH5c7",
# 				include_client_id=True,
# 				audience="https://api2.arduino.cc/iot",
# 		)

# 		# store access token in access_token variable
# 		access_token = token.get("access_token")
# 		# configure and instance the API client with our access_token
# 		client_config = iot.Configuration(host="https://api2.arduino.cc/iot")
# 		client_config.access_token = access_token
# 		api = None
# 		thing_id = None
# 		with iot.ApiClient(client_config) as client:
# 				# Create an instance of the API class
# 				api = iot.PropertiesV2Api(client)
# 				thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824"  # iPhone thing
# 				# thing_id = "a798decb-21e5-4b5f-a659-f4941437ae8f" # test_thing
# 		# client = iot.ApiClient(client_config)

# 		# Change this based on the device being used
# 		# thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824"

# 		# Custom variables for debugging
# 		looping = True  # whether the program continuously fetches data in a loop
# 		minutes_ago = 1  # how far back in time should the program fetch data, more minutes means longer fetch time
# 		# how many seconds should the program wait before fetching again
# 		sleep_duration = float(5)

# 		# init data for Properties API interactions
# 		# api = iot.PropertiesV2Api(client)
# 		prev_time_record = datetime.min  # reset prev_time_record

# 		# Change these property IDs based on info in the Thing setup page
# 		gps_id = "a058906f-caad-465b-96d3-da1981e81be7"
# 		gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146"
# 		acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5"

# 		property_id = gps_id
# 		# final output
# 		max_velocity = 0
# 		average_velocity = 0
# 		total_distance = 0
# 		total_calorie_burnt = 0
# 		coordinates = []
# 		velocity = []
# 		duration_list = []
# 		first_fetch = True
# 		interval_length = 0
# 		interval_length_for_sum = 0
# 		interval_length_for_list = 0
# 		previous_time = 0
# 		duration = 0
# 		while (True):
# 				try:
# 						now_time = datetime.now()
# 						if first_fetch == False:
# 								if now_time.second < previous_time.second:
# 										interval_length = now_time.second + 60 + (
# 												now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000)
# 										interval_length_for_sum = math.ceil((now_time.second + 60 + (
# 												now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000))*(10**9))/(10**9)
# 										interval_length_for_list = math.floor((now_time.second + 60 + (
# 												now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000))*(10**9))/(10**9)
# 								else:
# 										interval_length = now_time.second + \
# 												(now_time.microsecond/1000000) - previous_time.second - \
# 												(previous_time.microsecond/1000000)
# 										interval_length_for_sum = math.ceil(
# 												(now_time.second + (now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000))*(10**9))/(10**9)
# 										interval_length_for_list = math.floor(
# 												(now_time.second + (now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000))*(10**9))/(10**9)
# 								# interval length, not finished, datetime type issue
# 						previous_time = now_time
# 						print(f"Now:\t{now_time}")
# 						prev_time = now_time + timedelta(minutes=-minutes_ago)
# 						print(f"{minutes_ago} mins ago:\t{prev_time}")
# 						formatted_month = ('00' + str(prev_time.month))[-2:]
# 						formatted_date = ('00' + str(prev_time.day))[-2:]
# 						formatted_hour = ('00' + str(prev_time.hour - 7))[-2:]
# 						formatted_minute = ('00' + str(prev_time.minute))[-2:]
# 						formatted_second = ('00' + str(prev_time.second))[-2:]
# 						formatted_time = str(prev_time.year) + '-' + formatted_month + '-' + formatted_date + \
# 								'T' + formatted_hour + ':' + formatted_minute + ':' + formatted_second + 'Z'
# 						print(f"Formatted:\t{formatted_time}")

# 						# resp = api.properties_v2_list(thing_id)
# 						resp = api.properties_v2_show(thing_id, gps_id)
# 						# resp = api.properties_v2_timeseries(thing_id, property_id, desc=True, _from=formatted_time, interval=1)
# 						# if (len(resp.data) > 0):
# 						# 	print(f"Batch size: {len(resp.data)}")
# 						# 	if (resp.data[0].time != prev_time_record):
# 						# 		prev_time_record = resp.data[0].time
# 						# 		print(resp.data[0])
# 						# 	else:
# 						# 		print("No new records since last fetch")
# 						# else:
# 						# 	print(f"No records in last {minutes_ago} minutes")
# 						# print(resp)
# 						print(f"{resp.value_updated_at}\tGyroscope_X: {resp.last_value}")
# 						coordinates.append(
# 								tuple((resp._last_value['lat'], resp._last_value['lon'])))
# 						if first_fetch == True:
# 								first_fetch = False
# 						else:
# 								distance = haversine(coordinates[len(coordinates)-2][0], coordinates[len(
# 										coordinates)-2][1], coordinates[len(coordinates)-1][0], coordinates[len(coordinates)-1][0])
# 								total_distance += distance
# 								current_velocity = distance / interval_length
# 								duration += interval_length_for_sum
# 								max_velocity = max(max_velocity, current_velocity)
# 								velocity.append(current_velocity)
# 								duration_list.append(interval_length_for_list)
# 								print(current_velocity)
# 								print(distance)
# 								print(interval_length)
# 				except ApiException as e:
# 						print("Got an exception: {}".format(e))
# 				if len(velocity) >= 3:
# 						if coordinates[-1] == coordinates[-2] and coordinates[-2] == coordinates[-3]:
# 								summ = 0
# 								for i in range(0, len(velocity)-2):
# 										summ += i
# 								average_velocity = summ / len(velocity)
# 								session_dict = {
# 										'datetime': "25/06/2024",
# 										'duration': duration - duration_list[-1] - duration_list[-2] - duration_list[-3],
# 										'distance': total_distance,
# 										'avg': average_velocity,
# 										'max': max_velocity,
# 										'calories': 1000
# 								}
# 								running_sessions.append(session_dict)
# 								return redirect("/")
# 				print()
# 				time.sleep(sleep_duration)


@app.route("/finishsession")
@login_required
def finishsession():
    if arduino_cloud.session_done.is_set():
        if (can_add_to_db.is_set()):
            add_sessions_for(session['user_id'],
                             running_sessions=running_sessions)
            print("added newest session to database")
            can_add_to_db.clear()  # must run after everything else in if
        # global goal_distance
        # global goal_calories
        # global goal_flag
        if goal_flag:
            # show the finish message
            if (float(running_sessions[-1]['distance']) >= float(goal_distance)) and (float(running_sessions[-1]['calories']) >= float(goal_calories)):
                return render_template("status.html", flag=True)
            else:
                return render_template("status.html", flag=False)
        else:
            return redirect("/")
    else:
        # connection.close()
        # render_template("startsession.html")
        return redirect("/startsession")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    global running_sessions
    running_sessions = []
    # Redirect user to login form
    return redirect(url_for("login"))

# @app.route("/test")
# def test():
# 	return render_template("status.html", flag = True)


# if __name__ == "__main__":
print("before app start")
# app.run(debug=True)
print("after app start")
# while(True):
# 	pass
