import eventlet
import numpy as np
from scipy.optimize import least_squares
import json, math, time
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
import sqlite3
import datetime

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
    1: {"x": 1, "y": 0},
    2: {"x": 1, "y": 1},
    3: {"x": 0, "y": 1.},
}


# TxPower: RSSI value at 1 meter from the transmitter
# Bluetooth
# tx_power = -85

# WiFi
tx_power = -60

# Path loss exponent
n = 2


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


def rssi_to_distance(rssi, tx_power, n=3):
    return 10 ** ((tx_power - rssi) / (10 * n))


def trilateration(ap_coords, rssi_values, tx_power, n=2.5):
    # Convert RSSI values to distances
    distances = [rssi_to_distance(rssi, tx_power, n) for rssi in rssi_values]

    # Compute weights based on the distances
    weights = [1 / d for d in distances]
    weights = [w / sum(weights) for w in weights]  # Normalize the weights

    # Initial guess for the receiver position (center of the room)
    initial_guess = (
        np.mean([ap[0] for ap in ap_coords]),
        np.mean([ap[1] for ap in ap_coords]),
    )

    # Define residuals function
    def residuals(xy, *args):
        x, y = xy
        ap_coords, distances, weights = args
        return [
            weights[i] * (math.sqrt((x - ap_coords[i][0]) ** 2 + (y - ap_coords[i][1]) ** 2) - d)
            for i, d in enumerate(distances)
        ]

    # Perform weighted least-squares optimization
    result = least_squares(
        residuals, initial_guess, args=(ap_coords, distances, weights)
    )

    # Extract optimized receiver coordinates (X, Y)
    x, y = result.x

    return x, y


# Handles incoming RSSI values
@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print("RSSI Values received")
    data = dict(topic=message.topic, payload=message.payload.decode())
    print(data["payload"])
    try:
        values = json.loads(data["payload"])
    except Exception as e:
        print(e)
        return

    # Insert into database
    cursor = conn.cursor()
    query = "INSERT INTO rssi (node_id, date, value) \
      VALUES (?,?,?)"
    params = (int(values["node"]), int(time.time()), int(values["rssi"]))
    cursor.execute(query, params)
    conn.commit()

    # Triangulation, check if values meet requirement
    # At least 3 points meet requirements, within 2 seconds
    # 3 Points = Low Confident (Blue)
    # 4 Points = High Confident (Green)
    # Execute a SELECT statement to fetch the latest record
    # Define the time range
    time_range = datetime.datetime.now() - datetime.timedelta(seconds=10)

    # Query the database for the latest 5 seconds average RSSI value for each node
    cursor.execute(
        f"""SELECT node_id, AVG(value) as avg_rssi
            FROM rssi
            WHERE date >= {int(time_range.timestamp())} AND node_id IN (0, 1, 2, 3)
            GROUP BY node_id"""
    )

    # Fetch the result
    result = cursor.fetchall()
    cursor.close()

    print(result)

    # Check if there are at least 3 RSSI values for each node
    eligible_nodes = []
    for node_id, avg_rssi in result:
        eligible_nodes.append((node_id, avg_rssi))
    print(eligible_nodes)
    if len(eligible_nodes) < 3:
        print("Did not meet requirements")
        return

    if len(eligible_nodes) == 3:
        color = "blue"
    else:
        color = "green"

    points = []
    nodes = []
    for node_id, rssi in eligible_nodes:
        points.append(rssi)
        nodes.append((access_pointss[node_id]["x"], access_pointss[node_id]["y"]))

    x, y = trilateration(nodes, points, tx_power)
    if (x < 0):
        x = 0
    if (y < 0):
        y = 0
    if (x > 1):
        x = 1
    if (y > 1):
        y = 1
    print(f"x: {x}, y: {y}")

    if x != -1000:
        # socketio.emit("mqtt_message", data=data)

        socketio.emit(
            "my-state-update",
            {"x": int(x * 100 * 5), "y": int((1-y) * 100 * 5), "color": color},
        )
        app.config["MY_STATE"] = {
            "x": int(x * 100 * 5),
            "y": int((1-y) * 100 * 5),
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
