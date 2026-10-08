import csv
import re
import time
from pathlib import Path
from datetime import datetime

import serial

PORT = "COM6"
BAUD_RATE = 115200
RECORD_SECONDS = 20
COUNTDOWN_SECONDS = 3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = PROJECT_ROOT / "dataset"

CLASSES = [
    ("1", "exercise_1_loose_fist"),
    ("2", "exercise_2_fingertip_touching"),
    ("3", "exercise_3_wrist_rotation"),
    ("4", "exercise_4_finger_tapping"),
    ("5", "exercise_5_hand_wave"),
    ("6", "idle"),
]

HEADER = [
    "timestamp",
    "t1", "t2", "t3", "t4", "t5",
    "ax", "ay", "az",
    "gx", "gy", "gz",
    "label",
]

TOUCH_RE = re.compile(
    r"TOUCH:\s+"
    r"T1:(?P<t1>-?\d+(?:\.\d+)?)\s+"
    r"T2:(?P<t2>-?\d+(?:\.\d+)?)\s+"
    r"T3:(?P<t3>-?\d+(?:\.\d+)?)\s+"
    r"T4:(?P<t4>-?\d+(?:\.\d+)?)\s+"
    r"T5:(?P<t5>-?\d+(?:\.\d+)?)\s+\|\s+"
    r"ACC:\s+(?P<ax>-?\d+(?:\.\d+)?)\s+"
    r"(?P<ay>-?\d+(?:\.\d+)?)\s+"
    r"(?P<az>-?\d+(?:\.\d+)?)\s+\|\s+"
    r"GYRO:\s+(?P<gx>-?\d+(?:\.\d+)?)\s+"
    r"(?P<gy>-?\d+(?:\.\d+)?)\s+"
    r"(?P<gz>-?\d+(?:\.\d+)?)"
)

SENSOR_COLUMNS = [
    "t1", "t2", "t3", "t4", "t5",
    "ax", "ay", "az",
    "gx", "gy", "gz",
]


def next_filename(folder, label):
    number = 1

    while True:
        path = folder / f"{label}_{number}.csv"

        if not path.exists():
            return path

        number += 1


def parse_data_csv(line):
    parts = line.strip().split(",")

    if len(parts) != 13:
        return None

    if parts[0] != "DATA":
        return None

    try:
        values = [float(value) for value in parts[2:13]]
    except ValueError:
        return None

    return values


def parse_touch_debug(line):
    match = TOUCH_RE.search(line.strip())

    if match is None:
        return None

    try:
        return [
            float(match.group(column))
            for column in SENSOR_COLUMNS
        ]
    except ValueError:
        return None


def parse_data_line(line):
    return parse_data_csv(line) or parse_touch_debug(line)


def collect_recording(label):
    folder = RAW_ROOT / label
    folder.mkdir(parents=True, exist_ok=True)

    output_path = next_filename(folder, label)

    print()
    print("=" * 60)
    print(f"Recording: {label}")
    print(f"Output   : {output_path}")
    print("=" * 60)

    for remaining in range(COUNTDOWN_SECONDS, 0, -1):
        print(f"Starting in {remaining}...")
        time.sleep(1)

    print("RECORDING NOW - perform the exercise!")

    rows = []
    start_time = time.monotonic()

    try:
        ser = serial.Serial(
            PORT,
            BAUD_RATE,
            timeout=0.2
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not open {PORT}. "
            f"Close Serial Monitor/Plotter and try again.\n"
            f"Error: {error}"
        )

    time.sleep(1)
    ser.reset_input_buffer()

    try:
        while time.monotonic() - start_time < RECORD_SECONDS:
            raw = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not raw:
                continue

            values = parse_data_line(raw)

            if values is None:
                continue

            timestamp = datetime.now().isoformat(
                timespec="milliseconds"
            )

            rows.append([
                timestamp,
                *values,
                label
            ])

    finally:
        ser.close()

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(rows)

    print(f"Finished. Samples collected: {len(rows)}")
    print(f"Saved: {output_path}")

    return output_path, len(rows)


def main():
    RAW_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 70)
    print("GLOVECARE AI - REAL SENSOR DATA COLLECTION")
    print("=" * 70)

    print(f"Serial port : {PORT}")
    print(f"Baud rate   : {BAUD_RATE}")
    print(f"Duration    : {RECORD_SECONDS} seconds")

    print()
    print("IMPORTANT:")
    print("Only real ESP8266 + TTP223 + MPU6050 data is recorded.")
    print("No random or simulated sensor values are used.")
    print()

    while True:
        print("Choose class:")

        for key, label in CLASSES:
            print(f"{key}. {label}")

        print("q. Quit")

        choice = input("\nEnter choice: ").strip().lower()

        if choice == "q":
            break

        selected = None

        for key, label in CLASSES:
            if choice == key:
                selected = label
                break

        if selected is None:
            print("Invalid choice.")
            continue

        try:
            collect_recording(selected)

        except Exception as error:
            print()
            print(f"ERROR: {error}")

        again = input(
            "\nPress Enter to record another, "
            "or type q to quit: "
        )

        if again.strip().lower() == "q":
            break

    print("\nData collection stopped.")


if __name__ == "__main__":
    main()
