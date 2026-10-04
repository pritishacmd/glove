from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque
import numpy as np
import joblib
import os

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "model",
    "glovecare_model.pkl"
)

model = joblib.load(MODEL_PATH)

WINDOW_SIZE = 40

sensor_buffer = deque(maxlen=WINDOW_SIZE)

SENSOR_NAMES = [
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

FEATURE_NAMES = [
    "mean",
    "std",
    "min",
    "max",
    "range",
    "first",
    "last",
    "change",
    "mean_abs_change",
    "max_abs_change"
]


def create_features(samples):

    data = np.array(samples, dtype=float)

    features = []

    for column in range(data.shape[1]):

        values = data[:, column]

        mean_value = np.mean(values)
        std_value = np.std(values)
        min_value = np.min(values)
        max_value = np.max(values)
        range_value = max_value - min_value
        first_value = values[0]
        last_value = values[-1]
        change_value = last_value - first_value

        differences = np.diff(values)

        if len(differences) > 0:
            mean_abs_change = np.mean(np.abs(differences))
            max_abs_change = np.max(np.abs(differences))
        else:
            mean_abs_change = 0.0
            max_abs_change = 0.0

        features.extend([
            mean_value,
            std_value,
            min_value,
            max_value,
            range_value,
            first_value,
            last_value,
            change_value,
            mean_abs_change,
            max_abs_change
        ])

    return np.array(features).reshape(1, -1)


@app.route("/")
def home():

    return jsonify({
        "status": "OK",
        "message": "GloveCare AI API is running"
    })


@app.route("/health")
def health():

    return jsonify({
        "status": "OK",
        "model": "GloveCare Random Forest",
        "window_size": WINDOW_SIZE
    })


@app.route("/predict", methods=["POST"])
def predict():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "status": "ERROR",
                "message": "No sensor data received"
            }), 400

        sample = [
            float(data.get("t1", 0)),
            float(data.get("t2", 0)),
            float(data.get("t3", 0)),
            float(data.get("t4", 0)),
            float(data.get("t5", 0)),
            float(data.get("ax", 0)),
            float(data.get("ay", 0)),
            float(data.get("az", 0)),
            float(data.get("gx", 0)),
            float(data.get("gy", 0)),
            float(data.get("gz", 0))
        ]

        sensor_buffer.append(sample)

        if len(sensor_buffer) < WINDOW_SIZE:

            return jsonify({
                "status": "BUFFERING",
                "samples": len(sensor_buffer),
                "required": WINDOW_SIZE,
                "prediction": None,
                "confidence": 0
            })

        features = create_features(
            list(sensor_buffer)
        )

        prediction = model.predict(features)[0]

        probabilities = model.predict_proba(features)[0]

        confidence = float(np.max(probabilities))

        return jsonify({
            "status": "PREDICTED",
            "prediction": str(prediction),
            "confidence": confidence,
            "samples": len(sensor_buffer)
        })

    except Exception as error:

        print("Prediction error:", error)

        return jsonify({
            "status": "ERROR",
            "message": str(error)
        }), 500


@app.route("/reset", methods=["POST"])
def reset():

    sensor_buffer.clear()

    return jsonify({
        "status": "OK",
        "message": "Prediction buffer cleared"
    })


if __name__ == "__main__":

    print()
    print("====================================")
    print("       GLOVECARE AI API")
    print("====================================")
    print("Model loaded successfully")
    print("Window size:", WINDOW_SIZE)
    print("Features:", WINDOW_SIZE)
    print("API: http://127.0.0.1:8000")
    print("====================================")
    print()

    app.run(
        host="127.0.0.1",
        port=8000,
        debug=False
    )