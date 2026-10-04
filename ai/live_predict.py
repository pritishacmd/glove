import serial
import joblib
import numpy as np
import os
import math
import time

PORT = "COM6"
BAUD_RATE = 115200

WINDOW_SIZE = 40

MODEL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "model",
    "glovecare_model.pkl"
)

model = joblib.load(MODEL_FILE)

SENSORS = [
    "t1", "t2", "t3", "t4", "t5",
    "ax", "ay", "az",
    "gx", "gy", "gz"
]

NAMES = {
    "exercise_1_loose_fist": "Loose Fist",
    "exercise_2_fingers_straight": "Fingers Straight",
    "exercise_3_wrist_clockwise": "Wrist Clockwise",
    "exercise_4_hand_wave": "Hand Wave",
    "exercise_5_finger_typing": "Finger Typing",
    "idle": "Idle"
}


def calculate_features(window):

    features = []

    for sensor_index in range(11):

        values = []

        for row in window:
            values.append(row[sensor_index])

        mean_value = sum(values) / len(values)

        variance = 0

        for value in values:
            variance += (value - mean_value) ** 2

        variance = variance / len(values)

        std_value = math.sqrt(variance)

        minimum = min(values)
        maximum = max(values)

        value_range = maximum - minimum

        first_value = values[0]
        last_value = values[-1]

        change = last_value - first_value

        changes = []

        for i in range(1, len(values)):
            changes.append(
                values[i] - values[i - 1]
            )

        absolute_changes = []

        for change_value in changes:
            absolute_changes.append(
                abs(change_value)
            )

        mean_abs_change = (
            sum(absolute_changes)
            / len(absolute_changes)
        )

        max_abs_change = max(
            absolute_changes
        )

        features.append(mean_value)
        features.append(std_value)
        features.append(minimum)
        features.append(maximum)
        features.append(value_range)
        features.append(first_value)
        features.append(last_value)
        features.append(change)
        features.append(mean_abs_change)
        features.append(max_abs_change)

    return features


print()
print("========================================")
print("       GLOVECARE LIVE AI")
print("========================================")
print()

print("Connecting to ESP8266 on", PORT)

try:
    serial_port = serial.Serial(
        PORT,
        BAUD_RATE,
        timeout=1
    )

    time.sleep(2)

    print("Connected successfully.")
    print()
    print("Collecting 40 real sensor samples...")
    print()

except Exception as e:

    print()
    print("ERROR connecting to ESP8266:")
    print(e)
    exit()


window = []

try:

    while True:

        line = serial_port.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not line:
            continue

        if not line.startswith("DATA,"):
            continue

        values = line.split(",")

        if len(values) != 13:
            continue

        try:

            sensor_values = []

            for i in range(2, 13):
                sensor_values.append(
                    float(values[i])
                )

        except ValueError:
            continue

        window.append(sensor_values)

        if len(window) > WINDOW_SIZE:
            window.pop(0)

        if len(window) == WINDOW_SIZE:

            features = calculate_features(
                window
            )

            prediction = model.predict(
                np.array([features])
            )[0]

            if hasattr(model, "predict_proba"):

                probabilities = model.predict_proba(
                    np.array([features])
                )[0]

                confidence = max(
                    probabilities
                ) * 100

            else:
                confidence = 0

            print(
                "DETECTED:",
                NAMES.get(
                    prediction,
                    prediction
                ),
                "| Confidence:",
                f"{confidence:.1f}%"
            )

except KeyboardInterrupt:

    print()
    print("Live prediction stopped.")

finally:

    serial_port.close()