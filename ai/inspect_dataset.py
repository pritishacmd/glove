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


def read_file(filename):

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

                for sensor in SENSOR_COLUMNS:

                    values.append(
                        float(row[sensor])
                    )

                rows.append(values)

            except (ValueError, KeyError, TypeError):

                continue

    return rows


def calculate_std(values):

    if len(values) == 0:
        return 0

    mean_value = sum(values) / len(values)

    total = 0

    for value in values:

        total += (
            value - mean_value
        ) ** 2

    variance = total / len(values)

    return math.sqrt(variance)


def main():

    print()
    print("========================================")
    print("       GLOVECARE DATA INSPECTION")
    print("========================================")
    print()

    class_names = sorted(
        os.listdir(DATASET_FOLDER)
    )

    for label in class_names:

        folder = os.path.join(
            DATASET_FOLDER,
            label
        )

        if not os.path.isdir(folder):
            continue

        print("----------------------------------------")
        print("CLASS:", label)
        print("----------------------------------------")

        all_values = []

        for filename in sorted(
            os.listdir(folder)
        ):

            if not filename.lower().endswith(".csv"):
                continue

            filepath = os.path.join(
                folder,
                filename
            )

            rows = read_file(
                filepath
            )

            print(
                filename,
                "->",
                len(rows),
                "samples"
            )

            all_values.extend(rows)

        print()

        if len(all_values) == 0:

            print("No valid data found.")
            print()
            continue

        print("Sensor statistics:")
        print()

        for index, sensor in enumerate(
            SENSOR_COLUMNS
        ):

            values = []

            for row in all_values:

                values.append(
                    row[index]
                )

            minimum = min(values)
            maximum = max(values)
            mean = sum(values) / len(values)
            std = calculate_std(values)

            print(
                sensor,
                ":",
                "min =",
                round(minimum, 2),
                "max =",
                round(maximum, 2),
                "mean =",
                round(mean, 2),
                "std =",
                round(std, 2)
            )

        print()

        print("Touch sensor activity:")
        print()

        for index, sensor in enumerate(
            SENSOR_COLUMNS[:5]
        ):

            active_count = 0

            for row in all_values:

                if row[index] != 0:

                    active_count += 1

            percentage = (
                active_count
                / len(all_values)
            ) * 100

            print(
                sensor,
                "active:",
                round(percentage, 2),
                "%"
            )

        print()


if __name__ == "__main__":
    main()