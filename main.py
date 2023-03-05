import eventlet
import json, math
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO

eventlet.monkey_patch()

# Define the location
access_points = {
    "AP1": {"x": 0, "y": 0},
    "AP2": {"x": 0, "y": 500},
    "AP3": {"x": 500, "y": 0},
    "AP4": {"x": 500, "y": 500},
}

# Define a function to calculate the distance between the device and an access point
def distance(rssi):
    tx_power = -50  # The signal strength at 1 meter from the access point
    n = 2.0  # The path-loss exponent, typically ranging from 2.0 to 4.5
    return 10 ** ((tx_power - rssi) / (10 * n))


# Define a function to calculate the coordinates of the device's location
def triangulate(ap1, ap2, ap3, ap4):
    d1 = distance(ap1)
    d2 = distance(ap2)
    d3 = distance(ap3)
    d4 = distance(ap4)

    x1, y1 = access_points["AP1"]["x"], access_points["AP1"]["y"]
    x2, y2 = access_points["AP2"]["x"], access_points["AP2"]["y"]
    x3, y3 = access_points["AP3"]["x"], access_points["AP3"]["y"]
    x4, y4 = access_points["AP4"]["x"], access_points["AP4"]["y"]

    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = d1**2 - d2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = 2 * (x3 - x2)
    E = 2 * (y3 - y2)
    F = d2**2 - d3**2 - x2**2 + x3**2 - y2**2 + y3**2
    G = 2 * (x4 - x3)
    H = 2 * (y4 - y3)
    I = d3**2 - d4**2 - x3**2 + x4**2 - y3**2 + y4**2

    # Solve the system of linear equations
    x = (C * E - F * B) / (E * A - B * D)
    y = (C * D - A * F) / (B * D - A * E)

    # Use the fourth access point to refine the coordinates
    dx = x - x4
    dy = y - y4
    dr = math.sqrt(dx**2 + dy**2)
    d = d4 / dr
    x = x + dx * d
    y = y + dy * d

    return x, y


app = Flask(__name__)
app.config["SECRET"] = "my secret key"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MQTT_BROKER_URL"] = "broker.emqx.io"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_USERNAME"] = ""
app.config["MQTT_PASSWORD"] = ""
app.config["MQTT_KEEPALIVE"] = 5
app.config["MQTT_TLS_ENABLED"] = False

# Default market location
app.config["MY_STATE"] = {"x": int(50), "y": int(50)}


mqtt = Mqtt(app)
socketio = SocketIO(app)


# Subscribe to topic on start up
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe("testingtopic")


# Handles incoming RSSI values
@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(topic=message.topic, payload=message.payload.decode())
    node = json.loads(data["payload"])["node"]
    rssi = json.loads(data["payload"])["rssi"]
    x, y = triangulate(rssi, -30, -55, -60)
    # socketio.emit("mqtt_message", data=data)
    print(x, y)
    socketio.emit("my-state-update", {"x": int(x), "y": int(y)})
    app.config["MY_STATE"] = {"x": int(x), "y": int(y)}


# Logging
@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    print(level, buf)


# Home page
@app.route("/")
def index():
    my_state = app.config.get("MY_STATE", None)
    return render_template(
        "index_mqtt.html", x=my_state["x"], y=my_state["y"], APs=access_points
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, use_reloader=False, debug=True)
