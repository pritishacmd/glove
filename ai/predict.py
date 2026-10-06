from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATH SETUP
# ============================================================

AI_ROOT = Path(__file__).resolve().parent

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))


# ============================================================
# IMPORT FEATURE EXTRACTOR
# ============================================================

from feature_extractor import (
    extract_features,
    SENSOR_COLUMNS,
    WINDOW_SIZE
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    PROJECT_ROOT
    / "ai"
    / "model"
    / "glovecare_model.pkl"
)


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}\n"
            "Run train_model.py first."
        )

    package = joblib.load(MODEL_PATH)

    model = package["model"]

    feature_columns = package["feature_columns"]

    classes = package["classes"]

    window_size = package["window_size"]

    return (
        model,
        feature_columns,
        classes,
        window_size
    )


# ============================================================
# PREPARE RAW SENSOR WINDOW
# ============================================================

def prepare_window(data):

    if isinstance(data, pd.DataFrame):

        df = data.copy()

    else:

        df = pd.DataFrame(
            data,
            columns=SENSOR_COLUMNS
        )


    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in SENSOR_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Missing sensor columns: {missing_columns}"
        )


    # --------------------------------------------------------
    # Keep only raw sensor columns
    # --------------------------------------------------------

    df = df[SENSOR_COLUMNS].copy()


    # --------------------------------------------------------
    # Convert to numeric
    # --------------------------------------------------------

    for column in SENSOR_COLUMNS:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    df = df.dropna().reset_index(drop=True)


    # --------------------------------------------------------
    # Check window size
    # --------------------------------------------------------

    if len(df) < WINDOW_SIZE:

        raise ValueError(
            f"Need at least {WINDOW_SIZE} samples. "
            f"Received {len(df)}."
        )


    # Use latest 40 samples

    df = df.iloc[-WINDOW_SIZE:].copy()

    return df


# ============================================================
# CREATE FEATURE VECTOR
# ============================================================

def create_feature_vector(
    data,
    feature_columns
):

    # Prepare raw sensor data

    df = prepare_window(data)


    # Extract the same features used during training

    features = extract_features(df)


    # Check that every trained feature exists

    missing_features = [
        column
        for column in feature_columns
        if column not in features
    ]

    if missing_features:

        raise ValueError(
            "Missing trained features: "
            f"{missing_features}"
        )


    # Arrange features in EXACT training order

    feature_vector = np.asarray(
        [
            features[column]
            for column in feature_columns
        ],
        dtype=float
    )


    return feature_vector


# ============================================================
# PREDICT ONE RAW SENSOR WINDOW
# ============================================================

def predict_window(data):

    (
        model,
        feature_columns,
        classes,
        window_size
    ) = load_model()


    # Create 249-feature vector

    feature_vector = create_feature_vector(
        data,
        feature_columns
    )


    # Convert to DataFrame

    X = pd.DataFrame(
        [feature_vector],
        columns=feature_columns
    )


    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    prediction = model.predict(X)[0]


    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = None

    probabilities = None

    if hasattr(model, "predict_proba"):

        probabilities = model.predict_proba(X)[0]

        confidence = float(
            np.max(probabilities)
        )


    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = {
        "prediction": str(prediction),

        "confidence": confidence,

        "confidence_percent": (
            round(
                confidence * 100,
                2
            )
            if confidence is not None
            else None
        )
    }


    # Add probability of every class

    if probabilities is not None:

        result["probabilities"] = {

            str(class_name): round(
                float(probability),
                6
            )

            for class_name, probability
            in zip(
                classes,
                probabilities
            )
        }


    return result


# ============================================================
# TEST SAVED MODEL
# ============================================================

def main():

    print("=" * 60)

    print(
        "GloveCare AI - Prediction Module Test"
    )

    print("=" * 60)

    print()


    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    (
        model,
        feature_columns,
        classes,
        window_size
    ) = load_model()


    print(
        "Model loaded successfully."
    )

    print(
        f"Model type       : "
        f"{type(model).__name__}"
    )

    print(
        f"Features expected: "
        f"{len(feature_columns)}"
    )

    print(
        f"Window size      : "
        f"{window_size}"
    )

    print(
        f"Classes           : "
        f"{classes}"
    )

    print()


    # --------------------------------------------------------
    # Verify the trained feature configuration
    # --------------------------------------------------------

    if len(feature_columns) != 249:

        print(
            "WARNING: Expected 249 features, "
            f"but model contains {len(feature_columns)}."
        )

    else:

        print(
            "Feature configuration: OK"
        )


    if window_size != WINDOW_SIZE:

        print(
            "WARNING: Model window size does not "
            "match feature extractor."
        )

    else:

        print(
            "Window configuration: OK"
        )


    print()

    print(
        "Prediction module is ready for "
        "raw ESP8266 sensor data."
    )

    print()

    print("=" * 60)

    print(
        "NEXT STEP:"
    )

    print(
        "Connect the ESP8266 COM6 live sensor stream."
    )

    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()