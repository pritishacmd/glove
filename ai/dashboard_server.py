import argparse
import json
import math
import sys
import threading
import time
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import joblib
import pandas as pd
import serial


AI_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AI_ROOT.parent

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from feature_extractor import SENSOR_COLUMNS, WINDOW_SIZE, extract_features  # noqa: E402
from live_predict import parse_sensor_line  # noqa: E402


SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 115200
MODEL_PATH = AI_ROOT / "model" / "glovecare_model.pkl"
WINDOW_STRIDE = 20


class GloveState:
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.lock = threading.Lock()
        self.rows = deque(maxlen=160)
        self.latest = None
        self.connected = False
        self.error = None
        self.model_package = self._load_model()

    def _load_model(self):
        if not MODEL_PATH.exists():
            return None

        return joblib.load(MODEL_PATH)

    def start(self):
        thread = threading.Thread(
            target=self._read_serial_forever,
            daemon=True,
        )
        thread.start()

    def _read_serial_forever(self):
        while True:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as ser:
                    time.sleep(2)
                    ser.reset_input_buffer()

                    with self.lock:
                        self.connected = True
                        self.error = None

                    while True:
                        raw = ser.readline().decode(
                            "utf-8",
                            errors="ignore",
                        ).strip()

                        if not raw:
                            continue

                        row = parse_sensor_line(raw)

                        if row is None:
                            continue

                        with self.lock:
                            self.latest = row
                            self.rows.append(row)
                            self.connected = True
                            self.error = None

            except Exception as error:
                with self.lock:
                    self.connected = False
                    self.error = str(error)

                time.sleep(2)

    def sensor_payload(self):
        with self.lock:
            latest = dict(self.latest) if self.latest else None
            connected = self.connected
            error = self.error
            sample_count = len(self.rows)

        if latest is None:
            return {
                "connected": False,
                "sampleCount": sample_count,
                "error": error or "Waiting for sensor data",
            }

        ax = latest["ax"]
        ay = latest["ay"]
        az = latest["az"]
        gx = latest["gx"]
        gy = latest["gy"]
        gz = latest["gz"]
        touches = [
            int(latest["t1"]),
            int(latest["t2"]),
            int(latest["t3"]),
            int(latest["t4"]),
            int(latest["t5"]),
        ]

        ax_g = ax / 16384.0
        ay_g = ay / 16384.0
        az_g = az / 16384.0
        gx_dps = gx / 131.0
        gy_dps = gy / 131.0
        gz_dps = gz / 131.0

        pitch = math.degrees(
            math.atan2(ax_g, math.sqrt((ay_g * ay_g) + (az_g * az_g)))
        )
        roll = math.degrees(math.atan2(ay_g, az_g))

        return {
            "connected": connected,
            "sampleCount": sample_count,
            "timestamp": latest["timestamp"],
            "touch": touches,
            "accel": {
                "x": ax_g,
                "y": ay_g,
                "z": az_g,
            },
            "gyro": {
                "x": gx_dps,
                "y": gy_dps,
                "z": gz_dps,
            },
            "rawAccel": {
                "x": ax,
                "y": ay,
                "z": az,
            },
            "rawGyro": {
                "x": gx,
                "y": gy,
                "z": gz,
            },
            "orientation": {
                "pitch": pitch,
                "roll": roll,
            },
        }

    def prediction_payload(self):
        package = self.model_package

        if package is None:
            return {
                "ready": False,
                "error": f"Model not found: {MODEL_PATH}",
            }

        with self.lock:
            rows = list(self.rows)

        if len(rows) < WINDOW_SIZE:
            return {
                "ready": False,
                "error": (
                    f"Need {WINDOW_SIZE} samples, "
                    f"have {len(rows)}"
                ),
                "sampleCount": len(rows),
            }

        windows = []
        for start in range(
            max(0, len(rows) - WINDOW_SIZE - WINDOW_STRIDE),
            len(rows) - WINDOW_SIZE + 1,
            WINDOW_STRIDE,
        ):
            windows.append(rows[start:start + WINDOW_SIZE])

        if not windows:
            windows = [rows[-WINDOW_SIZE:]]

        model = package["model"]
        feature_columns = package["feature_columns"]
        classes = [str(class_name) for class_name in package["classes"]]
        probability_rows = []
        predictions = []

        for window in windows[-3:]:
            df = pd.DataFrame(window)[SENSOR_COLUMNS].copy()

            for column in SENSOR_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce")

            df = df.dropna().reset_index(drop=True)

            if len(df) != WINDOW_SIZE:
                continue

            features = extract_features(df)
            feature_df = pd.DataFrame(
                [
                    {
                        column: features[column]
                        for column in feature_columns
                    }
                ],
                columns=feature_columns,
            )
            predictions.append(str(model.predict(feature_df)[0]))
            probabilities = model.predict_proba(feature_df)[0]
            probability_rows.append(dict(zip(classes, probabilities)))

        if not probability_rows:
            return {
                "ready": False,
                "error": "No clean prediction window available",
                "sampleCount": len(rows),
            }

        averaged = {}

        for class_name in classes:
            averaged[class_name] = sum(
                row.get(class_name, 0.0)
                for row in probability_rows
            ) / len(probability_rows)

        prediction = max(averaged, key=averaged.get)
        confidence = averaged[prediction]

        return {
            "ready": True,
            "prediction": prediction,
            "confidence": confidence,
            "confidencePercent": round(confidence * 100, 2),
            "probabilities": {
                class_name: round(float(value), 6)
                for class_name, value in averaged.items()
            },
            "windowVotes": predictions,
            "sampleCount": len(rows),
        }


class DashboardHandler(SimpleHTTPRequestHandler):
    glove_state = None

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(
            *args,
            directory=str(PROJECT_ROOT),
            **kwargs,
        )

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/sensor":
            self._send_json(self.glove_state.sensor_payload())
            return

        if path == "/api/predict":
            self._send_json(self.glove_state.prediction_payload())
            return

        if path == "/":
            self.path = "/index.html"

        super().do_GET()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Serve the GloveCare dashboard with live USB glove data."
    )
    parser.add_argument("--port", default=SERIAL_PORT)
    parser.add_argument("--baud", type=int, default=BAUD_RATE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8000)
    return parser.parse_args()


def main():
    args = parse_args()
    state = GloveState(args.port, args.baud)
    state.start()
    DashboardHandler.glove_state = state

    server = ThreadingHTTPServer(
        (args.host, args.http_port),
        DashboardHandler,
    )

    print("=" * 70)
    print("GloveCare dashboard server running")
    print("=" * 70)
    print(f"Dashboard : http://{args.host}:{args.http_port}/dashboard.html")
    print(f"Login     : http://{args.host}:{args.http_port}/")
    print(f"Serial    : {args.port} @ {args.baud}")
    print("Press CTRL+C to stop.")
    print("=" * 70)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
