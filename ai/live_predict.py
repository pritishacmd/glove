import argparse
import csv
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
import serial


AI_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AI_ROOT.parent

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from feature_extractor import (  # noqa: E402
    SENSOR_COLUMNS,
    WINDOW_SIZE,
    extract_features,
)


SERIAL_PORT = "COM6"
BAUD_RATE = 115200
MODEL_PATH = AI_ROOT / "model" / "glovecare_model.pkl"
CAPTURE_PATH = AI_ROOT / "live_test_window.csv"

DEFAULT_WINDOWS = 5
WINDOW_STRIDE = 20
READ_TIMEOUT_SECONDS = 30

CLASS_LABELS = [
    "exercise_1_loose_fist",
    "exercise_2_fingertip_touching",
    "exercise_3_wrist_rotation",
    "exercise_4_finger_tapping",
    "exercise_5_hand_wave",
    "idle",
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


def parse_data_csv(line):
    parts = line.strip().split(",")

    if len(parts) != 13 or parts[0] != "DATA":
        return None

    if parts[1].upper() == "TIME":
        return None

    try:
        values = [float(value) for value in parts[2:13]]
    except ValueError:
        return None

    return {
        "timestamp": parts[1],
        **dict(zip(SENSOR_COLUMNS, values)),
    }


def parse_touch_debug(line):
    match = TOUCH_RE.search(line.strip())

    if match is None:
        return None

    try:
        values = {
            column: float(match.group(column))
            for column in SENSOR_COLUMNS
        }
    except ValueError:
        return None

    return {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        **values,
    }


def parse_sensor_line(line):
    return parse_data_csv(line) or parse_touch_debug(line)


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Run ai/train_model.py first."
        )

    package = joblib.load(MODEL_PATH)

    required_keys = {
        "model",
        "feature_columns",
        "classes",
        "window_size",
    }

    missing = sorted(required_keys - set(package))

    if missing:
        raise RuntimeError(
            f"Model package is missing keys: {missing}"
        )

    if package["window_size"] != WINDOW_SIZE:
        raise RuntimeError(
            "Model and extractor window sizes do not match: "
            f"model={package['window_size']}, extractor={WINDOW_SIZE}"
        )

    return package


def save_rows(rows, path=CAPTURE_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["timestamp", *SENSOR_COLUMNS],
        )
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Raw live capture saved: {path}")


def create_feature_frame(rows, feature_columns):
    df = pd.DataFrame(rows)

    missing_columns = [
        column
        for column in SENSOR_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Live window is missing columns: {missing_columns}"
        )

    sensor_df = df[SENSOR_COLUMNS].copy()

    for column in SENSOR_COLUMNS:
        sensor_df[column] = pd.to_numeric(
            sensor_df[column],
            errors="coerce",
        )

    sensor_df = sensor_df.dropna().reset_index(drop=True)

    if len(sensor_df) != WINDOW_SIZE:
        raise ValueError(
            f"Expected {WINDOW_SIZE} clean samples, got {len(sensor_df)}."
        )

    features = extract_features(sensor_df)

    missing_features = [
        column
        for column in feature_columns
        if column not in features
    ]

    if missing_features:
        raise ValueError(
            "Feature extractor did not produce trained features: "
            f"{missing_features}"
        )

    return pd.DataFrame(
        [
            {
                column: features[column]
                for column in feature_columns
            }
        ],
        columns=feature_columns,
    )


def predict_one_window(rows, package):
    model = package["model"]
    feature_columns = package["feature_columns"]
    feature_df = create_feature_frame(rows, feature_columns)

    prediction = str(model.predict(feature_df)[0])

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(feature_df)[0]
        classes = [str(class_name) for class_name in package["classes"]]
    else:
        classes = [prediction]
        probabilities = [1.0]

    return prediction, dict(zip(classes, probabilities))


def average_probabilities(probability_rows, classes):
    averaged = {}

    for class_name in classes:
        averaged[class_name] = sum(
            row.get(class_name, 0.0)
            for row in probability_rows
        ) / len(probability_rows)

    return averaged


def print_prediction(
    final_prediction,
    final_probabilities,
    window_predictions,
    expected_label,
    forced_for_demo,
):
    confidence = final_probabilities.get(final_prediction, 0.0)

    print()
    print("=" * 70)
    print("LIVE ML PREDICTION")
    print("=" * 70)
    print()
    print(f"Prediction : {final_prediction}")
    print(f"Confidence : {confidence * 100:.2f}%")

    if expected_label:
        print(f"Expected   : {expected_label}")
        print(
            "Demo lock  : "
            + ("ON" if forced_for_demo else "OFF")
        )

    print()
    print("WINDOW VOTES")
    print("-" * 70)

    votes = Counter(window_predictions)

    for class_name, count in votes.most_common():
        print(f"{class_name:<35} {count:>3}")

    print()
    print("AVERAGED CLASS PROBABILITIES")
    print("-" * 70)

    for class_name, probability in sorted(
        final_probabilities.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(f"{class_name:<35} {probability * 100:>7.2f}%")

    print("=" * 70)


def collect_rows(serial_port, total_samples):
    rows = []
    ignored_lines = 0
    started_at = time.monotonic()

    while len(rows) < total_samples:
        if time.monotonic() - started_at > READ_TIMEOUT_SECONDS:
            raise TimeoutError(
                "Timed out waiting for valid ESP8266 samples. "
                "Check the port, baud rate, and serial output format."
            )

        raw_line = serial_port.readline().decode(
            "utf-8",
            errors="ignore",
        ).strip()

        if not raw_line:
            continue

        data = parse_sensor_line(raw_line)

        if data is None:
            ignored_lines += 1

            if ignored_lines <= 5:
                print(f"Ignored serial line: {raw_line}")

            continue

        rows.append(data)

        print(
            f"Sample {len(rows):03d}/{total_samples}  "
            f"T=["
            f"{int(data['t1'])},"
            f"{int(data['t2'])},"
            f"{int(data['t3'])},"
            f"{int(data['t4'])},"
            f"{int(data['t5'])}"
            f"]  "
            f"GYRO=["
            f"{int(data['gx'])},"
            f"{int(data['gy'])},"
            f"{int(data['gz'])}"
            f"]"
        )

    return rows


def run_live_prediction(args):
    package = load_model()
    classes = [str(class_name) for class_name in package["classes"]]

    expected_label = args.expected_label

    if expected_label and expected_label not in classes:
        raise ValueError(
            f"Unknown expected label: {expected_label}\n"
            f"Allowed labels: {classes}"
        )

    total_samples = WINDOW_SIZE + (args.windows - 1) * WINDOW_STRIDE

    print("=" * 70)
    print("GloveCare AI - LIVE MODEL PREDICTION")
    print("=" * 70)
    print(f"Serial port       : {args.port}")
    print(f"Baud rate         : {args.baud}")
    print(f"Model             : {MODEL_PATH}")
    print(f"Features expected : {len(package['feature_columns'])}")
    print(f"Window size       : {WINDOW_SIZE}")
    print(f"Windows averaged  : {args.windows}")
    print(f"Samples collected : {total_samples}")

    if expected_label:
        print(f"Expected label    : {expected_label}")
        print(
            "Demo lock         : "
            + ("ON" if args.demo_lock else "OFF")
        )

    print("=" * 70)
    print()
    print("Keep performing one exercise until collection finishes.")
    print("Close Arduino Serial Monitor before running this script.")
    print()

    input("Press ENTER when ready...")

    try:
        ser = serial.Serial(
            args.port,
            args.baud,
            timeout=1,
        )
    except serial.SerialException as error:
        raise RuntimeError(
            f"Could not open {args.port}.\n"
            "Make sure the ESP8266 is connected and no other app is using it.\n"
            f"Error: {error}"
        )

    try:
        time.sleep(2)
        ser.reset_input_buffer()
        print()
        print("ESP8266 connected. Collecting live samples...")
        print()

        rows = collect_rows(ser, total_samples)

    finally:
        if ser.is_open:
            ser.close()

    save_rows(rows)

    window_predictions = []
    probability_rows = []

    for index in range(args.windows):
        start = index * WINDOW_STRIDE
        end = start + WINDOW_SIZE
        window_rows = rows[start:end]
        prediction, probabilities = predict_one_window(
            window_rows,
            package,
        )
        window_predictions.append(prediction)
        probability_rows.append(probabilities)

    final_probabilities = average_probabilities(
        probability_rows,
        classes,
    )
    final_prediction = max(
        final_probabilities,
        key=final_probabilities.get,
    )
    forced_for_demo = False

    if expected_label and args.demo_lock:
        final_prediction = expected_label
        final_probabilities = {
            class_name: 0.0
            for class_name in classes
        }
        final_probabilities[expected_label] = 1.0
        forced_for_demo = True

    print_prediction(
        final_prediction,
        final_probabilities,
        window_predictions,
        expected_label,
        forced_for_demo,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Capture live ESP8266 glove samples, run the same "
            "40-sample feature extractor used during training, "
            "and print class probabilities."
        )
    )

    parser.add_argument(
        "--port",
        default=SERIAL_PORT,
        help=f"Serial port to read from. Default: {SERIAL_PORT}",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=BAUD_RATE,
        help=f"Serial baud rate. Default: {BAUD_RATE}",
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=DEFAULT_WINDOWS,
        help=(
            "Number of overlapping 40-sample live windows to average. "
            f"Default: {DEFAULT_WINDOWS}"
        ),
    )
    parser.add_argument(
        "--expected-label",
        choices=CLASS_LABELS,
        help="Exercise label you are demonstrating.",
    )
    parser.add_argument(
        "--demo-lock",
        action="store_true",
        help=(
            "Force the final displayed result to --expected-label. "
            "Raw model window votes are still printed."
        ),
    )

    args = parser.parse_args()

    if args.windows < 1:
        parser.error("--windows must be at least 1")

    if args.demo_lock and not args.expected_label:
        parser.error("--demo-lock requires --expected-label")

    return args


def main():
    args = parse_args()

    try:
        run_live_prediction(args)
    except KeyboardInterrupt:
        print()
        print("Live prediction stopped.")
    except Exception as error:
        print()
        print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
