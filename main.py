import eventlet
import numpy as np
from scipy.optimize import least_squares
import json, math, time
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
import sqlite3

conn = sqlite3.connect("main.db")
eventlet.monkey_patch()

# Define the location for html
access_points = {
    "AP1": {"x": 0, "y": 0},
    "AP2": {"x": 490, "y": 10},
    "AP3": {"x": 500, "y": 490},
    "AP4": {"x": 10, "y": 500},
}

# Define the location
access_pointss = {
    0: {"x": 0, "y": 0},
    1: {"x": 10, "y": 0},
    2: {"x": 10, "y": 10},
    3: {"x": 0, "y": 10},
}


# TxPower: RSSI value at 1 meter from the transmitter
tx_power = -30

# Path loss exponent
n = 3


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MQTT_BROKER_URL"] = "broker.emqx.io"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_KEEPALIVE"] = 5
app.config["MQTT_TLS_ENABLED"] = False

# Default market location
app.config["MY_STATE"] = {"x": 250, "y": 250, "color": "Gray"}


mqtt = Mqtt(app)
socketio = SocketIO(app)
mqtt.subscribe("CSC2006")


def residuals(xy, *args):
    x, y = xy
    ap_coords, distances = args
    return [
        math.sqrt((x - ap[0]) ** 2 + (y - ap[1]) ** 2) - d
        for ap, d in zip(ap_coords, distances)
    ]


def rssi_to_distance(rssi, tx_power, n=3):
    return 10 ** ((tx_power - rssi) / (10 * n))


def trilateration(ap_coords, rssi_values, tx_power, n=3):
    # Convert RSSI values to distances
    distances = [rssi_to_distance(rssi, tx_power, n) for rssi in rssi_values]

    # Initial guess for the receiver position (center of the room)
    initial_guess = (
        np.mean([ap[0] for ap in ap_coords]),
        np.mean([ap[1] for ap in ap_coords]),
    )

    # Perform least-squares optimization
    result = least_squares(residuals, initial_guess, args=(ap_coords, distances))

    # Extract optimized receiver coordinates (X, Y)
    x, y = result.x

    return x, y


# Handles incoming RSSI values
@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print("RSSI Values received")
    data = dict(topic=message.topic, payload=message.payload.decode())
    values = json.loads(data["payload"])

    # Insert into database
    cursor = conn.cursor()
    query = "INSERT INTO rssi (node_id, date, value) \
      VALUES (?,?,?)"
    params = (values["node"], int(time.time()), values["value"])
    cursor.execute(query, params)
    conn.commit()

    # Triangulation, check if values meet requirement
    # At least 3 points meet requirements, within 2 seconds
    # 3 Points = Low Confident (Blue)
    # 4 Points = High Confident (Green)
    # Execute a SELECT statement to fetch the latest record
    withinTimeRequirement = 2
    cursor.execute(
        """SELECT rssi.node_id, rssi.value, rssi.date
    FROM rssi
    JOIN (
        SELECT node_id, MAX(date) AS max_date
        FROM rssi
        GROUP BY node_id
    ) AS latest
    ON rssi.node_id = latest.node_id AND rssi.date = latest.max_date"""
    )

    # Fetch the result
    result = cursor.fetchall()
    cursor.close()

    print(result)

    # Get highest / latest timestamp as upper limit
    maxTime = max(result[0][2], result[1][2], result[2][2], result[3][2])

    eligibleNodes = []
    for i in result:
        if maxTime - withinTimeRequirement <= i[2]:
            eligibleNodes.append(i)

    if len(eligibleNodes) < 3:
        print("Did not meet requirements")
        return

    if len(eligibleNodes) == 3:
        color = "blue"
    else:
        color = "green"

    points = []
    nodes = []
    for i in eligibleNodes:
        points.append(int(i[1]))
        nodes.append((access_pointss[i[0]]["x"], access_pointss[i[0]]["y"]))

    x, y = trilateration(nodes, points, tx_power)
    print(f"x: {x}, y: {y}")

    if x != -1000:
        # socketio.emit("mqtt_message", data=data)

        socketio.emit(
            "my-state-update",
            {"x": int(x * 100 / 2), "y": int(y * 100 / 2), "color": color},
        )
        app.config["MY_STATE"] = {
            "x": int(x * 100 / 2),
            "y": int(y * 100 / 2),
            "color": color,
        }


# Logging
@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    print(level, buf)


# Home page
@app.route("/")
def index():
    my_state = app.config.get("MY_STATE", None)
    return render_template(
        "index_mqtt.html",
        x=my_state["x"],
        y=my_state["y"],
        color=my_state["color"],
        APs=access_points,
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, use_reloader=False, debug=True)
