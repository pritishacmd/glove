import numpy as np
import pandas as pd


# ============================================================
# SENSOR CONFIGURATION
# ============================================================

SENSOR_COLUMNS = [
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
]


TOUCH_COLUMNS = [
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
]


IMU_COLUMNS = [
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
]


# Number of samples used for one ML window
WINDOW_SIZE = 40


# ============================================================
# BASIC STATISTICAL FEATURES
# ============================================================

def _add_stat_features(features, prefix, values):

    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return

    features[f"{prefix}_mean"] = float(
        np.mean(values)
    )

    features[f"{prefix}_std"] = float(
        np.std(values)
    )

    features[f"{prefix}_min"] = float(
        np.min(values)
    )

    features[f"{prefix}_max"] = float(
        np.max(values)
    )

    features[f"{prefix}_range"] = float(
        np.max(values) - np.min(values)
    )

    features[f"{prefix}_first"] = float(
        values[0]
    )

    features[f"{prefix}_last"] = float(
        values[-1]
    )

    features[f"{prefix}_change"] = float(
        values[-1] - values[0]
    )

    differences = np.diff(values)

    if len(differences) > 0:

        features[f"{prefix}_mean_abs_change"] = float(
            np.mean(np.abs(differences))
        )

        features[f"{prefix}_max_abs_change"] = float(
            np.max(np.abs(differences))
        )

    else:

        features[f"{prefix}_mean_abs_change"] = 0.0

        features[f"{prefix}_max_abs_change"] = 0.0

    features[f"{prefix}_energy"] = float(
        np.mean(values ** 2)
    )


# ============================================================
# TOUCH SENSOR FEATURES
# ============================================================

def _add_touch_features(features, df):

    touch = df[TOUCH_COLUMNS].astype(float)

    # --------------------------------------------------------
    # Individual finger statistics
    # --------------------------------------------------------

    for column in TOUCH_COLUMNS:

        values = touch[column].to_numpy()

        active = values > 0.5

        features[f"{column}_active_fraction"] = float(
            np.mean(active)
        )

        if len(active) > 1:

            changes = np.diff(
                active.astype(int)
            )

            on_events = np.sum(changes == 1)

            off_events = np.sum(changes == -1)

            transitions = np.sum(changes != 0)

        else:

            on_events = 0

            off_events = 0

            transitions = 0

        features[f"{column}_on_events"] = float(
            on_events
        )

        features[f"{column}_off_events"] = float(
            off_events
        )

        features[f"{column}_transitions"] = float(
            transitions
        )

        # ----------------------------------------------------
        # Longest ON and OFF duration
        # ----------------------------------------------------

        longest_on = 0

        longest_off = 0

        current_on = 0

        current_off = 0

        for state in active:

            if state:

                current_on += 1

                current_off = 0

            else:

                current_off += 1

                current_on = 0

            longest_on = max(
                longest_on,
                current_on
            )

            longest_off = max(
                longest_off,
                current_off
            )

        features[f"{column}_longest_on"] = float(
            longest_on
        )

        features[f"{column}_longest_off"] = float(
            longest_off
        )

    # ========================================================
    # FIVE-SENSOR STATE
    # ========================================================

    states = []

    for _, row in touch.iterrows():

        state = 0

        for index, column in enumerate(
            TOUCH_COLUMNS
        ):

            if row[column] > 0.5:

                state |= (1 << index)

        states.append(state)

    states = np.asarray(
        states,
        dtype=int
    )

    # --------------------------------------------------------
    # State fractions
    # --------------------------------------------------------

    for state in range(32):

        features[
            f"state_{state}_fraction"
        ] = float(
            np.mean(states == state)
        )

    # --------------------------------------------------------
    # State transitions
    # --------------------------------------------------------

    if len(states) > 1:

        state_changes = np.diff(states)

        features["state_transitions"] = float(
            np.sum(state_changes != 0)
        )

        features["state_mean_change"] = float(
            np.mean(np.abs(state_changes))
        )

        features["state_max_change"] = float(
            np.max(np.abs(state_changes))
        )

    else:

        features["state_transitions"] = 0.0

        features["state_mean_change"] = 0.0

        features["state_max_change"] = 0.0


# ============================================================
# FINGER ORDER FEATURES
# ============================================================

def _add_finger_order_features(features, df):

    touch = df[TOUCH_COLUMNS].astype(float)

    positions = []

    for _, row in touch.iterrows():

        active_positions = [
            index
            for index, column in enumerate(
                TOUCH_COLUMNS
            )
            if row[column] > 0.5
        ]

        if len(active_positions) == 0:

            positions.append(-1)

        else:

            positions.append(
                float(
                    np.mean(active_positions)
                )
            )

    positions = np.asarray(
        positions,
        dtype=float
    )

    valid = positions >= 0

    if np.any(valid):

        valid_positions = positions[valid]

        features["first_active_position"] = float(
            valid_positions[0]
        )

        features["last_active_position"] = float(
            valid_positions[-1]
        )

        features["active_center"] = float(
            np.mean(valid_positions)
        )

    else:

        features["first_active_position"] = -1.0

        features["last_active_position"] = -1.0

        features["active_center"] = -1.0

    # --------------------------------------------------------
    # Changes in active finger position
    # --------------------------------------------------------

    position_changes = []

    for i in range(1, len(positions)):

        previous = positions[i - 1]

        current = positions[i]

        if previous >= 0 and current >= 0:

            position_changes.append(
                current - previous
            )

    if len(position_changes) > 0:

        position_changes = np.asarray(
            position_changes,
            dtype=float
        )

        features["order_positive_fraction"] = float(
            np.mean(position_changes > 0)
        )

        features["order_negative_fraction"] = float(
            np.mean(position_changes < 0)
        )

        features["order_mean_change"] = float(
            np.mean(position_changes)
        )

        features["order_total_change"] = float(
            np.sum(position_changes)
        )

    else:

        features["order_positive_fraction"] = 0.0

        features["order_negative_fraction"] = 0.0

        features["order_mean_change"] = 0.0

        features["order_total_change"] = 0.0


# ============================================================
# FINGER-TO-FINGER TRANSITIONS
# ============================================================

def _add_finger_transition_features(features, df):

    touch = df[TOUCH_COLUMNS].astype(float)

    transitions = np.zeros(
        (5, 5),
        dtype=int
    )

    previous_finger = None

    for _, row in touch.iterrows():

        active = [
            index
            for index, column in enumerate(
                TOUCH_COLUMNS
            )
            if row[column] > 0.5
        ]

        if len(active) == 0:

            continue

        current_finger = active[0]

        if (
            previous_finger is not None
            and current_finger != previous_finger
        ):

            transitions[
                previous_finger,
                current_finger
            ] += 1

        previous_finger = current_finger

    for i in range(5):

        for j in range(5):

            if i != j:

                features[
                    f"finger_transition_{i+1}_{j+1}"
                ] = float(
                    transitions[i, j]
                )


# ============================================================
# ACCELEROMETER FEATURES
# ============================================================

def _add_accelerometer_features(features, df):

    ax = df["ax"].to_numpy(dtype=float)

    ay = df["ay"].to_numpy(dtype=float)

    az = df["az"].to_numpy(dtype=float)

    acceleration_magnitude = np.sqrt(
        ax ** 2
        + ay ** 2
        + az ** 2
    )

    _add_stat_features(
        features,
        "acc_magnitude",
        acceleration_magnitude
    )


# ============================================================
# GYROSCOPE FEATURES
# ============================================================

def _add_gyro_features(features, df):

    gx = df["gx"].to_numpy(dtype=float)

    gy = df["gy"].to_numpy(dtype=float)

    gz = df["gz"].to_numpy(dtype=float)

    gyro_magnitude = np.sqrt(
        gx ** 2
        + gy ** 2
        + gz ** 2
    )

    _add_stat_features(
        features,
        "gyro_magnitude",
        gyro_magnitude
    )

    # --------------------------------------------------------
    # Gyroscope direction changes
    # --------------------------------------------------------

    for axis_name, values in [
        ("gx", gx),
        ("gy", gy),
        ("gz", gz),
    ]:

        signs = np.sign(values)

        sign_changes = np.sum(
            signs[1:] != signs[:-1]
        )

        features[
            f"{axis_name}_sign_changes"
        ] = float(
            sign_changes
        )

        features[
            f"{axis_name}_positive_fraction"
        ] = float(
            np.mean(values > 0)
        )

        features[
            f"{axis_name}_negative_fraction"
        ] = float(
            np.mean(values < 0)
        )

    # --------------------------------------------------------
    # Gyroscope magnitude thresholds
    # --------------------------------------------------------

    thresholds = [
        50,
        100,
        250,
        500,
        1000,
    ]

    for threshold in thresholds:

        features[
            f"gyro_mag_above_{threshold}"
        ] = float(
            np.mean(
                gyro_magnitude > threshold
            )
        )


# ============================================================
# MAIN FEATURE EXTRACTION FUNCTION
# ============================================================

def extract_features(df):

    features = {}

    # --------------------------------------------------------
    # Make sure required columns exist
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
    # Copy only required columns
    # --------------------------------------------------------

    data = df[
        SENSOR_COLUMNS
    ].copy()

    # --------------------------------------------------------
    # Convert all values to numeric
    # --------------------------------------------------------

    for column in SENSOR_COLUMNS:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = data.dropna().reset_index(
        drop=True
    )

    if len(data) == 0:

        raise ValueError(
            "Window contains no valid sensor data."
        )

    # ========================================================
    # INDIVIDUAL SENSOR STATISTICS
    # ========================================================

    for column in SENSOR_COLUMNS:

        values = data[column].to_numpy(
            dtype=float
        )

        _add_stat_features(
            features,
            column,
            values
        )

    # ========================================================
    # TOUCH FEATURES
    # ========================================================

    _add_touch_features(
        features,
        data
    )

    # ========================================================
    # FINGER ORDER FEATURES
    # ========================================================

    _add_finger_order_features(
        features,
        data
    )

    # ========================================================
    # FINGER TRANSITION FEATURES
    # ========================================================

    _add_finger_transition_features(
        features,
        data
    )

    # ========================================================
    # ACCELEROMETER FEATURES
    # ========================================================

    _add_accelerometer_features(
        features,
        data
    )

    # ========================================================
    # GYROSCOPE FEATURES
    # ========================================================

    _add_gyro_features(
        features,
        data
    )

    return features


# ============================================================
# CREATE SORTED FEATURE VECTOR
# ============================================================

def feature_vector(df):

    features = extract_features(df)

    feature_names = sorted(
        features.keys()
    )

    vector = np.asarray(
        [
            features[name]
            for name in feature_names
        ],
        dtype=float
    )

    return vector, feature_names