import eventlet
import json, math, time
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
import sqlite3

conn = sqlite3.connect("main.db")
eventlet.monkey_patch()

# Define the location
access_points = {
    "AP1": {"x": 0, "y": 0},
    "AP2": {"x": 0, "y": 500},
    "AP3": {"x": 500, "y": 0},
    "AP4": {"x": 500, "y": 500},
}

# Define the location
access_pointss = {
    0: {"x": 0, "y": 0},
    1: {"x": 0, "y": 500},
    2: {"x": 500, "y": 0},
    3: {"x": 500, "y": 500},
}


# Define a function to calculate the distance between the device and an access point
def distance(rssi):
    tx_power = -50  # The signal strength at 1 meter from the access point
    n = 2.0  # The path-loss exponent, typically ranging from 2.0 to 4.5
    return 10 ** ((tx_power - rssi) / (10 * n))


# Define a function to calculate the coordinates of the device's location
def triangulate(points):
    """Returns the estimated (x, y) position of the receiver using triangulation.
    `points` is a list of tuples containing the (x, y, rssi) values of each access point.
    The function returns None if the number of points is less than 3 or greater than 4.
    """
    if len(points) < 3 or len(points) > 4:
        return None

    # Initialize variables
    x1, y1, rssi1 = points[0]
    x2, y2, rssi2 = points[1]
    x3, y3, rssi3 = points[2]
    A = B = C = D = 0

    # Calculate A, B, C, D coefficients
    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = rssi1**2 - rssi2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = 2 * (x3 - x2)
    E = 2 * (y3 - y2)
    F = rssi2**2 - rssi3**2 - x2**2 + x3**2 - y2**2 + y3**2

    # Calculate estimated (x, y) position
    x = (C * E - F * B) / (E * A - B * D)
    y = (C * D - A * F) / (B * D - A * E)

    if len(points) == 4:
        # If there are four points, calculate the average error
        errors = [math.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2) - p[2] for p in points]
        avg_error = sum(errors) / len(errors)
        if abs(avg_error) > 0.5:
            # If the average error is too high, return None
            return -1000, -1000

    return x, y


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MQTT_BROKER_URL"] = "broker.emqx.io"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_KEEPALIVE"] = 5
app.config["MQTT_TLS_ENABLED"] = False

# Default market location
app.config["MY_STATE"] = {"x": int(50), "y": int(50), "color": "Gray"}


mqtt = Mqtt(app)
socketio = SocketIO(app)
mqtt.subscribe("CSC2006")


# Subscribe to topic on start up
# @mqtt.on_connect()
# def handle_connect(client, userdata, flags, rc):
#     print("Subscribed")

# Sample data

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
    for i in eligibleNodes:
        points.append((access_pointss[i[0]]["x"], access_pointss[i[0]]["y"], int(i[1])))
    print(points)

    x, y = triangulate(points)
    print(f"x: {x}, y: {y}")

    if x != -1000:
        # socketio.emit("mqtt_message", data=data)

        socketio.emit("my-state-update", {"x": int(x), "y": int(y), "color": color})
        app.config["MY_STATE"] = {"x": int(x), "y": int(y), "color": color}


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
