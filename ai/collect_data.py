import serial
import csv
import os
import time

PORT = "COM6"
BAUD_RATE = 115200

RECORDING_DURATION = 20

DATASET_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dataset"
)

classes = {
    "1": "exercise_1_loose_fist",
    "2": "exercise_2_fingers_straight",
    "3": "exercise_3_wrist_clockwise",
    "4": "exercise_4_hand_wave",
    "5": "exercise_5_finger_typing",
    "6": "idle"
}


def choose_class():

    print()
    print("========================================")
    print("       GLOVECARE AI DATA COLLECTION")
    print("========================================")
    print()

    print("1. Loose Fist")
    print("2. Fingers Straight")
    print("3. Wrist Clockwise")
    print("4. Hand Wave")
    print("5. Finger Typing")
    print("6. Idle")
    print()

    choice = input("Enter choice (1-6): ")

    if choice not in classes:

        print("Invalid choice.")

        return None

    return classes[choice]


def collect_data(label):

    folder = os.path.join(
        DATASET_FOLDER,
        label
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    file_number = 1

    while os.path.exists(
        os.path.join(
            folder,
            f"{label}_{file_number}.csv"
        )
    ):
        file_number += 1

    filename = os.path.join(
        folder,
        f"{label}_{file_number}.csv"
    )

    print()
    print("Selected class:", label)
    print("Recording duration:", RECORDING_DURATION, "seconds")
    print("Saving data to:", filename)
    print()

    print("Get ready...")

    for i in range(3, 0, -1):

        print(i)

        time.sleep(1)

    print()
    print(">>> RECORDING STARTED <<<")
    print("Perform the selected movement now.")
    print("Recording will automatically stop after 20 seconds.")
    print()

    serial_port = None
    sample_count = 0

    try:

        serial_port = serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=1
        )

        time.sleep(2)

        start_time = time.time()

        with open(
            filename,
            "w",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "timestamp",
                "t1",
                "t2",
                "t3",
                "t4",
                "t5",
                "ax",
                "ay",
                "az",
                "gx",
                "gy",
                "gz",
                "label"
            ])

            while True:

                elapsed_time = time.time() - start_time

                if elapsed_time >= RECORDING_DURATION:
                    break

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

                    int(values[1])
                    int(values[2])
                    int(values[3])
                    int(values[4])
                    int(values[5])
                    int(values[6])
                    int(values[7])
                    int(values[8])
                    int(values[9])
                    int(values[10])
                    int(values[11])
                    int(values[12])

                except ValueError:

                    continue

                writer.writerow([
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    values[7],
                    values[8],
                    values[9],
                    values[10],
                    values[11],
                    values[12],
                    label
                ])

                sample_count += 1

                if sample_count % 20 == 0:

                    elapsed = time.time() - start_time
                    remaining = RECORDING_DURATION - elapsed

                    if remaining < 0:
                        remaining = 0

                    print(
                        "Samples:",
                        sample_count,
                        "| Time remaining:",
                        f"{remaining:.1f}",
                        "seconds"
                    )

    except KeyboardInterrupt:

        print()
        print("Recording manually stopped.")

    except serial.SerialException as e:

        print()
        print("ERROR: Could not open", PORT)
        print()
        print(e)
        print()
        print("Make sure:")
        print("1. ESP8266 is connected")
        print("2. The port is COM6")
        print("3. Serial Monitor is CLOSED")

    except Exception as e:

        print()
        print("ERROR:")
        print(e)

    finally:

        if serial_port is not None:
            serial_port.close()

        print()
        print(">>> RECORDING FINISHED <<<")
        print()
        print("Saved file:")
        print(filename)
        print()
        print("Total samples:", sample_count)
        print("Expected approximately:", RECORDING_DURATION * 20)
        print()


while True:

    label = choose_class()

    if label is None:
        continue

    collect_data(label)

    print()

    again = input(
        "Collect another recording? (y/n) "
    )

    if again.lower() != "y":
        break

print()
print("========================================")
print("       DATA COLLECTION FINISHED")
print("========================================")