import math

# Access point coordinates
AP1 = (0, 0)
AP2 = (10, 0)
AP3 = (10, 10)
AP4 = (0, 10)
ap_coords = [AP1, AP2, AP3, AP4]

# Sample RSSI values
RSSI_AP1 = -1
RSSI_AP2 = -120
RSSI_AP3 = -120
RSSI_AP4 = -120
rssi_values = [RSSI_AP1, RSSI_AP2, RSSI_AP3, RSSI_AP4]

# TxPower: RSSI value at 1 meter from the transmitter
tx_power = -30

# Path loss exponent
n = 3
def distance(rssi):
    tx_power = -50  # The signal strength at 1 meter from the access point
    n = 2.0  # The path-loss exponent, typically ranging from 2.0 to 4.5
    return 10 ** ((tx_power - rssi) / (10 * n))

def rssi_to_distance(rssi, tx_power, n=3):
    return 10 ** ((tx_power - rssi) / (10 * n))

def trilateration(ap_coords, rssi_values, tx_power, n=3):
    # Convert RSSI values to distances
    distances = [rssi_to_distance(rssi, tx_power, n) for rssi in rssi_values]

    # Check if there are 3 or 4 access points
    if len(ap_coords) == 3:
        A, B, C = ap_coords
        a, b, c = distances

        # Calculate using trilateration equations
        W = b * b - a * a - (B[0] - A[0]) * (B[0] - A[0]) - (B[1] - A[1]) * (B[1] - A[1])
        Z = c * c - a * a - (C[0] - A[0]) * (C[0] - A[0]) - (C[1] - A[1]) * (C[1] - A[1])
        P = 2 * ((B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]))

        # Calculate receiver's position (X, Y)
        x = A[0] + ((W * (C[1] - A[1]) - Z * (B[1] - A[1])) / P)
        y = A[1] + ((Z * (B[0] - A[0]) - W * (C[0] - A[0])) / P)

    elif len(ap_coords) == 4:
        A, B, C, D = ap_coords
        a, b, c, d = distances

        # Perform trilateration with AP1, AP2, AP3
        x1, y1 = trilateration([A, B, C], [a, b, c], tx_power, n)

        # Perform trilateration with AP1, AP3, AP4
        x2, y2 = trilateration([A, C, D], [a, c, d], tx_power, n)

        # Find the average position to improve accuracy
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2

    else:
        raise ValueError("Invalid number of access points.")

    return x, y

print(trilateration(ap_coords,rssi_values,tx_power))