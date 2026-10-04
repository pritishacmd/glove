import os
import csv
import math

PROJECT_FOLDER = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "dataset"
)

OUTPUT_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "ai",
    "dataset"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "processed_windows.csv"
)

WINDOW_SIZE = 40
STEP_SIZE = 20

SENSOR_COLUMNS = [
    "t1", "t2", "t3", "t4", "t5",
    "ax", "ay", "az",
    "gx", "gy", "gz"
]

GOOD_RECORDINGS = {
    "exercise_1_loose_fist": [4, 5, 6, 7, 8, 9],
    "exercise_2_fingers_straight": [4, 5, 6, 7, 8, 9],
    "exercise_3_wrist_clockwise": [4, 5, 6, 7, 8, 10],
    "exercise_4_hand_wave": [4, 5, 6, 7, 8, 9],
    "exercise_5_finger_typing": [4, 5, 6, 7, 8, 9],
    "idle": [4, 5, 6, 7, 8, 9]
}


def read_recording(filename):

    rows = []

    with open(filename, "r", newline="") as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:

                values = []

                for sensor in SENSOR_COLUMNS:
                    values.append(float(row[sensor]))

                rows.append(values)

            except (ValueError, KeyError, TypeError):
                continue

    return rows


def calculate_features(window):

    features = []

    for sensor_index in range(len(SENSOR_COLUMNS)):

        values = []

        for row in window:
            values.append(row[sensor_index])

        mean_value = sum(values) / len(values)

        variance = 0

        for value in values:
            variance += (value - mean_value) ** 2

        variance = variance / len(values)

        std_value = math.sqrt(variance)

        minimum = min(values)
        maximum = max(values)

        value_range = maximum - minimum

        first_value = values[0]
        last_value = values[-1]

        change = last_value - first_value

        changes = []

        for i in range(1, len(values)):
            changes.append(
                values[i] - values[i - 1]
            )

        absolute_changes = []

        for change_value in changes:
            absolute_changes.append(
                abs(change_value)
            )

        if len(absolute_changes) > 0:
            mean_abs_change = (
                sum(absolute_changes)
                / len(absolute_changes)
            )

            max_abs_change = max(
                absolute_changes
            )
        else:
            mean_abs_change = 0
            max_abs_change = 0

        features.append(mean_value)
        features.append(std_value)
        features.append(minimum)
        features.append(maximum)
        features.append(value_range)
        features.append(first_value)
        features.append(last_value)
        features.append(change)
        features.append(mean_abs_change)
        features.append(max_abs_change)

    return features


def main():

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    print()
    print("========================================")
    print("     GLOVECARE AI PREPROCESSING")
    print("========================================")
    print()

    all_windows = []

    total_recordings = 0
    total_windows = 0

    for label in GOOD_RECORDINGS:

        print()
        print("Class:", label)

        folder = os.path.join(
            DATASET_FOLDER,
            label
        )

        recording_numbers = GOOD_RECORDINGS[label]

        for recording_number in recording_numbers:

            filename = (
                f"{label}_{recording_number}.csv"
            )

            filepath = os.path.join(
                folder,
                filename
            )

            if not os.path.exists(filepath):

                print(
                    "WARNING: File not found:",
                    filename
                )

                continue

            rows = read_recording(filepath)

            if len(rows) < WINDOW_SIZE:

                print(
                    "WARNING: Not enough samples:",
                    filename
                )

                continue

            recording_id = (
                f"{label}_{recording_number}"
            )

            recording_windows = 0

            start = 0

            while start + WINDOW_SIZE <= len(rows):

                window = rows[
                    start:start + WINDOW_SIZE
                ]

                features = calculate_features(
                    window
                )

                all_windows.append(
                    (
                        features,
                        label,
                        recording_id
                    )
                )

                recording_windows += 1
                total_windows += 1

                start += STEP_SIZE

            total_recordings += 1

            print(
                filename,
                "| Samples:",
                len(rows),
                "| Windows:",
                recording_windows
            )

    feature_count = len(
        all_windows[0][0]
    )

    header = []

    for sensor in SENSOR_COLUMNS:

        header.append(sensor + "_mean")
        header.append(sensor + "_std")
        header.append(sensor + "_min")
        header.append(sensor + "_max")
        header.append(sensor + "_range")
        header.append(sensor + "_first")
        header.append(sensor + "_last")
        header.append(sensor + "_change")
        header.append(sensor + "_mean_abs_change")
        header.append(sensor + "_max_abs_change")

    header.append("label")
    header.append("recording_id")

    with open(
        OUTPUT_FILE,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(header)

        for features, label, recording_id in all_windows:

            writer.writerow(
                features
                + [label, recording_id]
            )

    print()
    print("========================================")
    print("       PREPROCESSING COMPLETE")
    print("========================================")
    print()

    print(
        "Recordings used:",
        total_recordings
    )

    print(
        "Windows created:",
        total_windows
    )

    print(
        "Features per window:",
        feature_count
    )

    print()
    print("Output file:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()