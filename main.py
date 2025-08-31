from flask import Flask, render_template, request
import json
import datetime
from pytz import timezone
from geopy.distance import geodesic

SYD = timezone("Australia/Sydney")

app = Flask(__name__)

with open("passwords.json", "r") as f:
    passwords = json.load(f)
# Password: Person name
try:
    with open("data.json", "r") as f:
        stored = json.load(f)
except FileNotFoundError:
    stored = {}

def roundDownDateTime(dt):
    delta_min = dt.minute % 5
    return datetime.datetime(dt.year, dt.month, dt.day,
                             dt.hour, dt.minute - delta_min, 0, 0)

@app.route("/ping")
def ping():
    return "Pong"

@app.route("/send_loc")
def send_loc():
    pass

@app.route("/")
def serve_page():
    password = request.args.get("password")

    if password not in passwords:
        return "No access", 401
    
    default_pos = [-33.8679, 151.207]

    return render_template("index.html", default_pos=default_pos)

@app.route("/send_data", methods=["POST"])
def send_data():
    password = request.args.get("password")

    if password not in passwords:
        return "No access", 401

    user = passwords[password]
    data = request.get_json()
    pos = data["pos"]

    now = roundDownDateTime(datetime.datetime.now(SYD)).strftime("%H:%M")

    if now not in data:
        stored[now] = {user: (pos[0], pos[1])}
    else:
        stored[now][user] = (pos[0], pos[1])

    with open("data.json", "w") as f:
        json.dump(stored, f)

    return "success"

@app.route("/get_data")
def get_data():
    password = request.args.get("password")

    if password not in passwords:
        return "No access", 401

    user = passwords[password]

    try:
        time = list(stored.keys())[-1]
        latest = stored[time]
    except IndexError:
        time = None
    try:
        prev_time = list(stored.keys())[-2]
        prev = stored[prev_time]
    except IndexError:
        prev_time = None

    output = []

    if time is not None:

        own_location = latest[user]

        for i in latest:
            if i != user or True:
                speed = round(geodesic(prev[i], latest[i]).km / 5 * 60, 2) if prev_time is not None else "Unknown"
                user_data = {
                    "user": i,
                    "pos": latest[i],
                    "diff": round(geodesic(latest[i], own_location).km, 2),
                    "speed": speed,
                    "update_time": time
                }

                output.append(user_data)

    return output
            

app.run(debug=True)