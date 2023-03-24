import numpy as np
from scipy.optimize import least_squares
import math


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


# Access Point coordinates (assuming a 10x10 meter square room)
AP1 = (0, 0)
AP2 = (10, 0)
AP3 = (10, 10)
AP4 = (0, 10)

ap_coords = [AP1, AP2, AP3, AP4]

# Sample RSSI values (in dBm)
RSSI1 = -10
RSSI2 = -65
RSSI3 = -70
RSSI4 = -30

rssi_values = [RSSI1, RSSI2, RSSI3, RSSI4]

# TxPower value at 1 meter from the transmitter (in dBm)
tx_power = -30

# Example usage of the trilateration function
receiver_coords = trilateration(ap_coords, rssi_values, tx_power)
print(f"Receiver coordinates: {receiver_coords}")
