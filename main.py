import math

# Define the known locations and signal strengths of the APs
APs = {
    "AP1": {"location": (0, 0), "tx_power": 200},
    "AP2": {"location": (0, 500), "tx_power": 200},
    "AP3": {"location": (500, 0), "tx_power": 200},
    "AP4": {"location": (500, 500), "tx_power": 200},
}

# Define the propagation exponent
n = 2

# Collect the RSSI values from the device
RSSIs = {"AP1": -50, "AP2": -55, "AP3": -60}

# Calculate the distances between the device and each AP
distances = {}
for AP, RSSI in RSSIs.items():
    distance = 10 ** ((APs[AP]["tx_power"] - RSSI) / (10 * n))
    distances[AP] = distance

# Calculate the device's position using triangulation
x1, y1 = APs["AP1"]["location"]
x2, y2 = APs["AP2"]["location"]
x3, y3 = APs["AP3"]["location"]
r1, r2, r3 = distances.values()

A = 2 * x2 - 2 * x1
B = 2 * y2 - 2 * y1
C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
D = 2 * x3 - 2 * x2
E = 2 * y3 - 2 * y2
F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2

x = (C * E - F * B) / (E * A - B * D)
y = (C * D - A * F) / (B * D - A * E)

# Display the device's position on a webpage
# (Assuming you have a Flask app set up already)
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    print(x, y)
    return render_template("index.html", x=50, y=50, APs=APs, circle=700)


if __name__ == "__main__":
    app.run()
