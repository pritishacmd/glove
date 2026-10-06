from pathlib import Path
import sys
import random
import pandas as pd


# ============================================================
# MAKE THE ai FOLDER AVAILABLE FOR IMPORTS
# ============================================================

AI_ROOT = Path(__file__).resolve().parent

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))


from feature_extractor import (
    extract_features,
    SENSOR_COLUMNS,
    WINDOW_SIZE
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_ROOT = PROJECT_ROOT / "dataset"

PROCESSED_ROOT = (
    PROJECT_ROOT
    / "ai"
    / "dataset"
    / "processed"
)

PROCESSED_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CONFIGURATION
# ============================================================

CLASSES = [
    "exercise_1_loose_fist",
    "exercise_2_fingertip_touching",
    "exercise_3_wrist_rotation",
    "exercise_4_finger_tapping",
    "exercise_5_hand_wave",
    "idle",
]

WINDOW_STEP = 20

TEST_RECORDINGS_PER_CLASS = 2

RANDOM_SEED = 42


# ============================================================
# RANDOM SEED
# ============================================================

random.seed(RANDOM_SEED)


# ============================================================
# LOAD ONE RECORDING
# ============================================================

def load_recording(csv_path):

    df = pd.read_csv(csv_path)

    missing_columns = [
        column
        for column in SENSOR_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:

        print(
            f"WARNING: Skipping {csv_path.name} "
            f"because columns are missing: {missing_columns}"
        )

        return None

    df = df[SENSOR_COLUMNS].copy()

    for column in SENSOR_COLUMNS:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna().reset_index(drop=True)

    return df


# ============================================================
# CREATE WINDOWS
# ============================================================

def create_windows(df):

    windows = []

    if len(df) < WINDOW_SIZE:
        return windows

    for start in range(
        0,
        len(df) - WINDOW_SIZE + 1,
        WINDOW_STEP
    ):

        end = start + WINDOW_SIZE

        window = df.iloc[start:end].copy()

        windows.append(
            (
                start,
                window
            )
        )

    return windows


# ============================================================
# PROCESS RECORDINGS
# ============================================================

def process_recordings(
    recordings,
    label
):

    rows = []

    for csv_path in recordings:

        df = load_recording(csv_path)

        if df is None:
            continue

        if len(df) < WINDOW_SIZE:

            print(
                f"WARNING: Skipping {csv_path.name} "
                f"because it has only {len(df)} samples."
            )

            continue

        windows = create_windows(df)

        # Unique ID for this complete recording
        recording_id = (
            f"{label}__{csv_path.stem}"
        )

        for window_start, window in windows:

            try:

                features = extract_features(window)

                row = dict(features)

                # Metadata required for grouped validation
                row["recording_id"] = recording_id

                row["label"] = label

                row["window_start"] = window_start

                rows.append(row)

            except Exception as error:

                print(
                    f"WARNING: Feature extraction failed for "
                    f"{csv_path.name}: {error}"
                )

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "GloveCare AI - Dataset Preprocessing"
    )

    print("=" * 60)

    print()

    print(
        f"Raw dataset:       {RAW_ROOT}"
    )

    print(
        f"Processed dataset: {PROCESSED_ROOT}"
    )

    print()


    # ========================================================
    # FIND ALL RECORDINGS
    # ========================================================

    all_recordings = {}

    total_recordings = 0

    for class_name in CLASSES:

        class_dir = RAW_ROOT / class_name

        if not class_dir.exists():

            print(
                f"WARNING: Folder not found: {class_dir}"
            )

            all_recordings[class_name] = []

            continue

        recordings = sorted(
            class_dir.glob("*.csv")
        )

        all_recordings[class_name] = recordings

        total_recordings += len(recordings)


    print(
        f"Total recordings found: {total_recordings}"
    )

    print()


    # ========================================================
    # RECORDING-LEVEL TRAIN / TEST SPLIT
    # ========================================================

    train_recordings = {}

    test_recordings = {}

    for class_name in CLASSES:

        recordings = list(
            all_recordings[class_name]
        )

        if len(recordings) == 0:

            train_recordings[class_name] = []

            test_recordings[class_name] = []

            continue

        random.shuffle(recordings)

        if len(recordings) <= TEST_RECORDINGS_PER_CLASS:

            test_count = 1

        else:

            test_count = TEST_RECORDINGS_PER_CLASS

        test_set = recordings[:test_count]

        train_set = recordings[test_count:]

        train_recordings[class_name] = train_set

        test_recordings[class_name] = test_set


    # ========================================================
    # PRINT TRAINING RECORDINGS
    # ========================================================

    print("TRAIN:")

    for class_name in CLASSES:

        print(
            f"{class_name}: "
            f"{len(train_recordings[class_name])}"
        )

    print()


    # ========================================================
    # PRINT TEST RECORDINGS
    # ========================================================

    print("TEST:")

    for class_name in CLASSES:

        print(
            f"{class_name}: "
            f"{len(test_recordings[class_name])}"
        )

    print()


    # ========================================================
    # SAVE RECORDING SPLIT
    # ========================================================

    train_recording_rows = []

    for class_name in CLASSES:

        for csv_path in train_recordings[class_name]:

            train_recording_rows.append(
                {
                    "recording": csv_path.name,
                    "path": str(csv_path),
                    "label": class_name
                }
            )


    test_recording_rows = []

    for class_name in CLASSES:

        for csv_path in test_recordings[class_name]:

            test_recording_rows.append(
                {
                    "recording": csv_path.name,
                    "path": str(csv_path),
                    "label": class_name
                }
            )


    train_recording_df = pd.DataFrame(
        train_recording_rows
    )

    test_recording_df = pd.DataFrame(
        test_recording_rows
    )


    train_recording_df.to_csv(
        PROCESSED_ROOT / "train_recordings.csv",
        index=False
    )

    test_recording_df.to_csv(
        PROCESSED_ROOT / "test_recordings.csv",
        index=False
    )


    # ========================================================
    # CREATE TRAINING FEATURES
    # ========================================================

    print("Creating training windows...")

    train_rows = []

    for class_name in CLASSES:

        rows = process_recordings(
            train_recordings[class_name],
            class_name
        )

        train_rows.extend(rows)


    # ========================================================
    # CREATE TEST FEATURES
    # ========================================================

    print("Creating testing windows...")

    test_rows = []

    for class_name in CLASSES:

        rows = process_recordings(
            test_recordings[class_name],
            class_name
        )

        test_rows.extend(rows)


    # ========================================================
    # CONVERT TO DATAFRAMES
    # ========================================================

    train_df = pd.DataFrame(
        train_rows
    )

    test_df = pd.DataFrame(
        test_rows
    )


    # ========================================================
    # VALIDATE
    # ========================================================

    if train_df.empty:

        raise RuntimeError(
            "Training dataset is empty. "
            "Check your raw CSV files and feature extractor."
        )


    if test_df.empty:

        raise RuntimeError(
            "Testing dataset is empty. "
            "Check your raw CSV files and feature extractor."
        )


    # ========================================================
    # KEEP METADATA IN A FIXED ORDER
    # ========================================================

    metadata_columns = [
        "recording_id",
        "label",
        "window_start"
    ]


    feature_columns = [
        column
        for column in train_df.columns
        if column not in metadata_columns
    ]


    # Make sure both datasets contain the same feature columns

    missing_test_features = [
        column
        for column in feature_columns
        if column not in test_df.columns
    ]


    if missing_test_features:

        raise RuntimeError(
            "Testing dataset is missing feature columns: "
            f"{missing_test_features}"
        )


    train_df = train_df[
        feature_columns + metadata_columns
    ]


    test_df = test_df[
        feature_columns + metadata_columns
    ]


    # ========================================================
    # SAVE PROCESSED DATA
    # ========================================================

    train_path = (
        PROCESSED_ROOT / "train.csv"
    )

    test_path = (
        PROCESSED_ROOT / "test.csv"
    )


    train_df.to_csv(
        train_path,
        index=False
    )

    test_df.to_csv(
        test_path,
        index=False
    )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()

    print("=" * 60)

    print(
        "PREPROCESSING COMPLETE"
    )

    print("=" * 60)

    print()

    print(
        f"Training windows: {len(train_df)}"
    )

    print(
        f"Testing windows : {len(test_df)}"
    )

    print(
        f"Features/window : {len(feature_columns)}"
    )

    print(
        f"Training recordings: "
        f"{train_df['recording_id'].nunique()}"
    )

    print(
        f"Testing recordings : "
        f"{test_df['recording_id'].nunique()}"
    )

    print()

    print("Saved training data:")

    print(train_path)

    print()

    print("Saved testing data:")

    print(test_path)

    print()

    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()