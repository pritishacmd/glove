import serial
import time
import csv
import os
import joblib
import pandas as pd

from ai.feature_extractor import extract_features, SENSOR_COLUMNS, WINDOW_SIZE


# ============================================================
# SERIAL SETTINGS
# ============================================================

SERIAL_PORT = "COM6"
BAUD_RATE = 115200


# ============================================================
# MODEL SETTINGS
# ============================================================

MODEL_PATH = r".\ai\model\glovecare_model.pkl"

CAPTURE_PATH = r".\ai\live_test_window.csv"


# ============================================================
# PARSE ESP8266 DATA
# ============================================================

def parse_sensor_line(line):

    line = line.strip()

    if not line:
        return None

    if not line.startswith("DATA,"):
        return None

    parts = line.split(",")

    if len(parts) != 13:
        return None

    # Ignore CSV header
    if parts[1] == "TIME":
        return None

    try:

        data = {
            "time": parts[1],

            "t1": float(parts[2]),
            "t2": float(parts[3]),
            "t3": float(parts[4]),
            "t4": float(parts[5]),
            "t5": float(parts[6]),

            "ax": float(parts[7]),
            "ay": float(parts[8]),
            "az": float(parts[9]),

            "gx": float(parts[10]),
            "gy": float(parts[11]),
            "gz": float(parts[12])
        }

        return data

    except ValueError:

        return None


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not os.path.exists(MODEL_PATH):

        print()
        print("ERROR: Model file not found.")
        print()
        print("Expected:")
        print(MODEL_PATH)
        print()

        return None

    package = joblib.load(MODEL_PATH)

    model = package["model"]
    feature_columns = package["feature_columns"]
    classes = package["classes"]

    print()
    print("MODEL LOADED")
    print("-" * 70)
    print(f"Model type       : {type(model).__name__}")
    print(f"Features expected: {len(feature_columns)}")
    print(f"Window size      : {package['window_size']}")
    print(f"Classes          : {list(classes)}")
    print("-" * 70)

    return package


# ============================================================
# SAVE RAW LIVE WINDOW
# ============================================================

def save_window(rows):

    os.makedirs(os.path.dirname(CAPTURE_PATH), exist_ok=True)

    fieldnames = [
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
        "gz"
    ]

    with open(
        CAPTURE_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in rows:

            writer.writerow({
                "timestamp": row["time"],
                "t1": row["t1"],
                "t2": row["t2"],
                "t3": row["t3"],
                "t4": row["t4"],
                "t5": row["t5"],
                "ax": row["ax"],
                "ay": row["ay"],
                "az": row["az"],
                "gx": row["gx"],
                "gy": row["gy"],
                "gz": row["gz"]
            })

    print()
    print(f"Raw live window saved to:")
    print(CAPTURE_PATH)


# ============================================================
# PREDICT LIVE WINDOW
# ============================================================

def predict_window(rows, package):

    model = package["model"]
    feature_columns = package["feature_columns"]

    # Convert the 40 real sensor samples into a DataFrame
    df = pd.DataFrame(rows)

    # Keep EXACTLY the same raw sensor columns used during training
    df = df[SENSOR_COLUMNS]

    # Extract the same 249 features used during training
    features = extract_features(df)

    # Arrange features in EXACT trained order
    feature_values = {
        column: features[column]
        for column in feature_columns
    }

    feature_df = pd.DataFrame(
        [feature_values],
        columns=feature_columns
    )

    # Prediction
    prediction = model.predict(feature_df)[0]

    probabilities = model.predict_proba(feature_df)[0]

    classes = list(model.classes_)

    # Sort probabilities from highest to lowest
    results = sorted(
        zip(classes, probabilities),
        key=lambda x: x[1],
        reverse=True
    )

    confidence = max(probabilities) * 100

    print()
    print("=" * 70)
    print("LIVE ML PREDICTION")
    print("=" * 70)

    print()
    print(f"Prediction : {prediction}")
    print(f"Confidence : {confidence:.2f}%")

    print()
    print("ALL CLASS PROBABILITIES")
    print("-" * 70)

    for class_name, probability in results:

        print(
            f"{class_name:<35} "
            f"{probability * 100:>7.2f}%"
        )

    print("-" * 70)

    print()
    print(f"Samples used  : {len(df)}")
    print(f"Features used : {len(feature_columns)}")

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("GloveCare AI - LIVE MODEL DIAGNOSTIC TEST")
    print("=" * 70)

    print()
    print(f"Serial port : {SERIAL_PORT}")
    print(f"Baud rate   : {BAUD_RATE}")
    print(f"Window size : {WINDOW_SIZE} samples")
    print()

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    package = load_model()

    if package is None:
        return

    # --------------------------------------------------------
    # Check window size
    # --------------------------------------------------------

    if WINDOW_SIZE != 40:

        print()
        print("ERROR: Expected window size is 40.")
        print(f"Current window size: {WINDOW_SIZE}")
        return

    # --------------------------------------------------------
    # Connect to ESP8266
    # --------------------------------------------------------

    print()
    print("Connecting to ESP8266...")

    try:

        ser = serial.Serial(
            SERIAL_PORT,
            BAUD_RATE,
            timeout=1
        )

    except serial.SerialException as error:

        print()
        print("ERROR: Could not open COM6.")
        print()
        print(error)
        print()
        print("Make sure:")
        print("1. ESP8266 is connected.")
        print("2. COM6 is correct.")
        print("3. Arduino Serial Monitor is CLOSED.")
        print("4. No other program is using COM6.")

        return

    # Give serial connection time to initialize
    time.sleep(2)

    # Remove old buffered data
    ser.reset_input_buffer()

    print()
    print("ESP8266 connected successfully.")

    print()
    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)
    print()
    print("We will collect EXACTLY 40 consecutive REAL sensor samples.")
    print()
    print("Perform ONE exercise continuously while the samples are")
    print("being collected.")
    print()
    print("For the first test, perform:")
    print()
    print("        LOOSE FIST")
    print()
    print("Keep doing the exercise until collection finishes.")
    print()
    print("Do NOT use Arduino Serial Monitor.")
    print()
    print("=" * 70)

    input("Press ENTER when you are ready...")

    print()
    print("STARTING COLLECTION...")
    print()

    rows = []

    try:

        while len(rows) < WINDOW_SIZE:

            raw_line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not raw_line:
                continue

            data = parse_sensor_line(raw_line)

            if data is None:
                continue

            rows.append(data)

            print(
                f"Sample {len(rows):02d}/{WINDOW_SIZE}  "
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

        print()
        print("=" * 70)
        print("40 SAMPLES COLLECTED")
        print("=" * 70)

        # ----------------------------------------------------
        # Save raw live data
        # ----------------------------------------------------

        save_window(rows)

        # ----------------------------------------------------
        # Run ML prediction
        # ----------------------------------------------------

        predict_window(rows, package)

    except KeyboardInterrupt:

        print()
        print()
        print("Test stopped by user.")

    finally:

        if ser.is_open:
            ser.close()

        print()
        print("COM6 disconnected.")


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()