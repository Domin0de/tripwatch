from flask import Flask, render_template, request
import json
import datetime
from pytz import timezone
from geopy.distance import geodesic
from random import random

from werkzeug.middleware.proxy_fix import ProxyFix


SYD = timezone("Australia/Sydney")

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

with open("passwords.json", "r") as f:
    passwords = json.load(f)
# Password: Person name
try:
    with open("data.json", "r") as f:
        stored = json.load(f)
except FileNotFoundError:
    stored = {}

with open("cars.json", "r") as f:
    cars = json.load(f)

def roundDownDateTime(dt):
    delta_min = dt.minute % 5
    return datetime.datetime(dt.year, dt.month, dt.day,
                             dt.hour, dt.minute - delta_min, 0, 0)

def moderateData(location):
    if random() > 0.5:
        return location + random() / 100

    return location - random() / 100

@app.route("/ping")
def ping():
    return "Pong"

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
    if user == "Admin":
        return "success"

    data = request.get_json()
    pos = data["pos"]

    now = roundDownDateTime(datetime.datetime.now(SYD)).strftime("%d-%m-%y %H:%M %p")

    if now not in stored:
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
    except IndexError:
        time = None

    output = []

    if time is not None:
        try:
            own_occurs = [j for j in stored.keys() if user in stored[j]][-1]
            own_location = stored[own_occurs][user]
        except:
            own_location = None

        for i in cars:
            if i != user:
                occurs = [j for j in stored.keys() if i in stored[j]]
                latest_occur = occurs[-1] if occurs else None
                prev_occur = occurs[-2] if occurs and len(occurs) > 1 else None

                latest = stored[latest_occur] if latest_occur else {}
                prev = stored[prev_occur] if prev_occur else {}

                if not latest:
                    continue

                if prev_occur:
                    time_diff = (
                        datetime.datetime.strptime(latest_occur, "%d-%m-%y %H:%M %p") - datetime.datetime.strptime(prev_occur, "%d-%m-%y %H:%M %p")
                    ).total_seconds() / 60
                    speed = round(geodesic(prev[i], latest[i]).km / time_diff * 60, 2)
                else:
                    speed = "Unknown"

                user_data = {
                    "user": i,
                    "pos": (moderateData(latest[i][0]), moderateData(latest[i][1])),
                    "diff": round(geodesic(latest[i], own_location).km, 2) if own_location else "Unknown",
                    "speed": speed,
                    "update_time": latest_occur,
                    "car": cars[i]
                }

                output.append(user_data)

    return output

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int("5000"), debug=True)
