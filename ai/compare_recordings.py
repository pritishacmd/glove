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

SENSOR_COLUMNS = [
    "t1", "t2", "t3", "t4", "t5",
    "ax", "ay", "az",
    "gx", "gy", "gz"
]


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


def calculate_statistics(rows):

    statistics = []

    for sensor_index in range(len(SENSOR_COLUMNS)):

        values = []

        for row in rows:
            values.append(row[sensor_index])

        if len(values) == 0:
            statistics.append(
                (
                    0,
                    0,
                    0,
                    0
                )
            )

            continue

        mean_value = sum(values) / len(values)

        variance = 0

        for value in values:
            variance += (value - mean_value) ** 2

        variance = variance / len(values)

        std_value = math.sqrt(variance)

        minimum = min(values)
        maximum = max(values)

        statistics.append(
            (
                mean_value,
                std_value,
                minimum,
                maximum
            )
        )

    return statistics


def print_recording(label, filename, rows):

    print()
    print("----------------------------------------")
    print("Class:", label)
    print("Recording:", filename)
    print("Samples:", len(rows))
    print("----------------------------------------")

    if len(rows) == 0:

        print("WARNING: No valid sensor data found.")
        print("This recording will need to be checked.")
        return

    statistics = calculate_statistics(rows)

    print(
        f"{'Sensor':<6}"
        f"{'Mean':>12}"
        f"{'Std':>12}"
        f"{'Min':>12}"
        f"{'Max':>12}"
    )

    for i in range(len(SENSOR_COLUMNS)):

        sensor = SENSOR_COLUMNS[i]

        mean_value = statistics[i][0]
        std_value = statistics[i][1]
        minimum = statistics[i][2]
        maximum = statistics[i][3]

        print(
            f"{sensor:<6}"
            f"{mean_value:>12.1f}"
            f"{std_value:>12.1f}"
            f"{minimum:>12.1f}"
            f"{maximum:>12.1f}"
        )


def main():

    print()
    print("========================================")
    print("   GLOVECARE RECORDING COMPARISON")
    print("========================================")
    print()

    class_folders = []

    for name in sorted(os.listdir(DATASET_FOLDER)):

        folder = os.path.join(
            DATASET_FOLDER,
            name
        )

        if os.path.isdir(folder):
            class_folders.append(name)

    print("Classes found:", len(class_folders))

    for label in class_folders:

        folder = os.path.join(
            DATASET_FOLDER,
            label
        )

        files = []

        for filename in sorted(os.listdir(folder)):

            if filename.lower().endswith(".csv"):
                files.append(filename)

        print()
        print("========================================")
        print("CLASS:", label)
        print("========================================")
        print("Recordings:", len(files))

        for filename in files:

            filepath = os.path.join(
                folder,
                filename
            )

            rows = read_recording(filepath)

            print_recording(
                label,
                filename,
                rows
            )

    print()
    print("========================================")
    print("       COMPARISON COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()