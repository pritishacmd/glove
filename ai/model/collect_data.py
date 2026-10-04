import csv
import os
import time
import serial

PORT = "COM5"
BAUD_RATE = 115200

EXERCISES = {
    "1": "exercise_1_loose_fist",
    "2": "exercise_2_fingers_straight",
    "3": "exercise_3_wrist_clockwise",
    "4": "exercise_4_hand_wave",
    "5": "exercise_5_finger_typing"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

print("===================================")
print("       GLOVECARE AI")
print("     SENSOR DATA COLLECTOR")
print("===================================")

print()
print("Select exercise:")

for number, exercise in EXERCISES.items():
    print(number + ". " + exercise)

choice = input("\nEnter exercise number: ").strip()

if choice not in EXERCISES:
    print("Invalid exercise number.")
    exit()

exercise_name = EXERCISES[choice]
exercise_folder = os.path.join(DATASET_DIR, exercise_name)

os.makedirs(exercise_folder, exist_ok=True)

session_number = 1

while True:
    filename = f"session_{session_number:02d}.csv"
    filepath = os.path.join(exercise_folder, filename)

    if not os.path.exists(filepath):
        break

    session_number += 1

print()
print("Selected exercise:", exercise_name)
print("Output file:", filepath)

input("\nPress ENTER when the glove is ready...")

try:
    ser = serial.Serial(
        PORT,
        BAUD_RATE,
        timeout=1
    )

    time.sleep(2)

except serial.SerialException as error:
    print()
    print("Could not open the serial port.")
    print("Current port:", PORT)
    print()
    print("Make sure the ESP8266 is connected.")
    print("Error:", error)
    exit()

headers = [
    "timestamp",
    "touch_1",
    "touch_2",
    "touch_3",
    "touch_4",
    "touch_5",
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "label"
]

with open(filepath, "w", newline="") as file:

    writer = csv.writer(file)
    writer.writerow(headers)

    print()
    print("Recording started.")
    print("Perform the exercise.")
    print("Press CTRL+C to stop.")
    print()

    try:

        while True:

            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not line:
                continue

            if not line.startswith("TOUCH:"):
                continue

            try:
                parts = line.split("|")

                touch_part = parts[0].strip()
                acc_part = parts[1].strip()
                gyro_part = parts[2].strip()

                touch_values = []

                for item in touch_part.replace(
                    "TOUCH:", ""
                ).split():

                    if ":" in item:
                        value = item.split(":")[1]
                        touch_values.append(int(value))

                acc_values = acc_part.replace(
                    "ACC:",
                    ""
                ).strip().split()

                gyro_values = gyro_part.replace(
                    "GYRO:",
                    ""
                ).strip().split()

                if len(touch_values) != 5:
                    continue

                if len(acc_values) != 3:
                    continue

                if len(gyro_values) != 3:
                    continue

                timestamp = time.time()

                row = [
                    timestamp,
                    touch_values[0],
                    touch_values[1],
                    touch_values[2],
                    touch_values[3],
                    touch_values[4],
                    acc_values[0],
                    acc_values[1],
                    acc_values[2],
                    gyro_values[0],
                    gyro_values[1],
                    gyro_values[2],
                    exercise_name
                ]

                writer.writerow(row)
                file.flush()

                print(row)

            except (ValueError, IndexError):
                continue

except KeyboardInterrupt:

    print()
    print("Recording stopped.")

finally:

    ser.close()

print()
print("===================================")
print("Recording saved successfully.")
print("File:", filepath)
print("===================================")