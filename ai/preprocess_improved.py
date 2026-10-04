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
    "processed_windows_improved.csv"
)

WINDOW_SIZE = 40


RAW_COLUMNS = [
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


FEATURE_NAMES = []


for sensor in [
    "t1",
    "t2",
    "t3",
    "t4",
    "t5"
]:

    FEATURE_NAMES.append(
        sensor + "_mean"
    )

    FEATURE_NAMES.append(
        sensor + "_std"
    )

    FEATURE_NAMES.append(
        sensor + "_active"
    )


for sensor in [
    "acc_magnitude",
    "gyro_magnitude"
]:

    FEATURE_NAMES.append(
        sensor + "_mean"
    )

    FEATURE_NAMES.append(
        sensor + "_std"
    )

    FEATURE_NAMES.append(
        sensor + "_min"
    )

    FEATURE_NAMES.append(
        sensor + "_max"
    )

    FEATURE_NAMES.append(
        sensor + "_range"
    )

    FEATURE_NAMES.append(
        sensor + "_mean_abs_change"
    )

    FEATURE_NAMES.append(
        sensor + "_max_abs_change"
    )


for sensor in [
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz"
]:

    FEATURE_NAMES.append(
        sensor + "_mean"
    )

    FEATURE_NAMES.append(
        sensor + "_std"
    )

    FEATURE_NAMES.append(
        sensor + "_range"
    )


def read_recording(filename):

    rows = []

    with open(
        filename,
        "r",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:

                values = []

                for column in RAW_COLUMNS:

                    values.append(
                        float(row[column])
                    )

                rows.append(values)

            except (
                ValueError,
                KeyError,
                TypeError
            ):

                continue

    return rows


def mean(values):

    return sum(values) / len(values)


def standard_deviation(values):

    average = mean(values)

    total = 0

    for value in values:

        total += (
            value - average
        ) ** 2

    return math.sqrt(
        total / len(values)
    )


def mean_absolute_change(values):

    if len(values) < 2:

        return 0

    total = 0

    for i in range(1, len(values)):

        total += abs(
            values[i] - values[i - 1]
        )

    return total / (
        len(values) - 1
    )


def max_absolute_change(values):

    if len(values) < 2:

        return 0

    maximum = 0

    for i in range(1, len(values)):

        change = abs(
            values[i] - values[i - 1]
        )

        if change > maximum:

            maximum = change

    return maximum


def calculate_features(window):

    features = []

    # ------------------------------------
    # TOUCH SENSOR FEATURES
    # ------------------------------------

    for sensor_index in range(5):

        values = []

        for row in window:

            values.append(
                row[sensor_index]
            )

        sensor_mean = mean(values)

        sensor_std = standard_deviation(
            values
        )

        active_count = 0

        for value in values:

            if value == 1:

                active_count += 1

        active_percentage = (
            active_count
            / len(values)
        )

        features.append(
            sensor_mean
        )

        features.append(
            sensor_std
        )

        features.append(
            active_percentage
        )

    # ------------------------------------
    # CALCULATE ACCELERATION MAGNITUDE
    # ------------------------------------

    acceleration_values = []

    for row in window:

        ax = row[5]
        ay = row[6]
        az = row[7]

        magnitude = math.sqrt(
            ax * ax
            + ay * ay
            + az * az
        )

        acceleration_values.append(
            magnitude
        )

    # ------------------------------------
    # CALCULATE GYRO MAGNITUDE
    # ------------------------------------

    gyro_values = []

    for row in window:

        gx = row[8]
        gy = row[9]
        gz = row[10]

        magnitude = math.sqrt(
            gx * gx
            + gy * gy
            + gz * gz
        )

        gyro_values.append(
            magnitude
        )

    # ------------------------------------
    # IMU MAGNITUDE FEATURES
    # ------------------------------------

    for values in [
        acceleration_values,
        gyro_values
    ]:

        features.append(
            mean(values)
        )

        features.append(
            standard_deviation(values)
        )

        features.append(
            min(values)
        )

        features.append(
            max(values)
        )

        features.append(
            max(values) - min(values)
        )

        features.append(
            mean_absolute_change(values)
        )

        features.append(
            max_absolute_change(values)
        )

    # ------------------------------------
    # RAW IMU FEATURES
    # ------------------------------------

    for sensor_index in range(
        5,
        11
    ):

        values = []

        for row in window:

            values.append(
                row[sensor_index]
            )

        features.append(
            mean(values)
        )

        features.append(
            standard_deviation(values)
        )

        features.append(
            max(values) - min(values)
        )

    return features


def main():

    print()
    print("========================================")
    print("    GLOVECARE IMPROVED PREPROCESSING")
    print("========================================")
    print()

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    all_windows = []

    total_files = 0
    total_windows = 0

    class_folders = []

    for name in sorted(
        os.listdir(DATASET_FOLDER)
    ):

        folder = os.path.join(
            DATASET_FOLDER,
            name
        )

        if os.path.isdir(folder):

            class_folders.append(
                name
            )

    print(
        "Classes found:",
        len(class_folders)
    )

    print()

    for label in class_folders:

        folder = os.path.join(
            DATASET_FOLDER,
            label
        )

        print(
            "Processing:",
            label
        )

        files = []

        for filename in sorted(
            os.listdir(folder)
        ):

            if filename.lower().endswith(
                ".csv"
            ):

                files.append(
                    filename
                )

        print(
            "  Recordings:",
            len(files)
        )

        for filename in files:

            filepath = os.path.join(
                folder,
                filename
            )

            rows = read_recording(
                filepath
            )

            total_files += 1

            print(
                "  ",
                filename,
                "->",
                len(rows),
                "valid samples"
            )

            window_number = 1

            start = 0

            while (
                start + WINDOW_SIZE
                <= len(rows)
            ):

                window = rows[
                    start:
                    start + WINDOW_SIZE
                ]

                features = calculate_features(
                    window
                )

                recording_id = os.path.splitext(
                    filename
                )[0]

                all_windows.append(
                    [
                        recording_id,
                        window_number,
                        label
                    ]
                    + features
                )

                total_windows += 1

                window_number += 1

                start += WINDOW_SIZE

        print()

    header = [
        "recording_id",
        "window_number",
        "label"
    ] + FEATURE_NAMES

    with open(
        OUTPUT_FILE,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            header
        )

        writer.writerows(
            all_windows
        )

    print("========================================")
    print("   IMPROVED PREPROCESSING COMPLETE")
    print("========================================")
    print()

    print(
        "Total recordings:",
        total_files
    )

    print(
        "Total windows:",
        total_windows
    )

    print(
        "Features per window:",
        len(FEATURE_NAMES)
    )

    print()

    print(
        "Output file:"
    )

    print(
        OUTPUT_FILE
    )

    print()

    print("========================================")


if __name__ == "__main__":

    main()