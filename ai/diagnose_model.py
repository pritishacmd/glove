import os
import csv

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix


PROJECT_FOLDER = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PROCESSED_FILE = os.path.join(
    PROJECT_FOLDER,
    "ai",
    "dataset",
    "processed_windows.csv"
)


def read_dataset():

    features = []
    labels = []

    with open(
        PROCESSED_FILE,
        "r",
        newline=""
    ) as file:

        reader = csv.reader(file)

        next(reader)

        for row in reader:

            if len(row) < 4:
                continue

            label = row[2]

            try:

                values = []

                for value in row[3:]:

                    values.append(
                        float(value)
                    )

            except ValueError:

                continue

            features.append(values)
            labels.append(label)

    return features, labels


def main():

    print()
    print("========================================")
    print("       GLOVECARE MODEL DIAGNOSTIC")
    print("========================================")
    print()

    X, y = read_dataset()

    print(
        "Total windows:",
        len(X)
    )

    print(
        "Features:",
        len(X[0])
    )

    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print(
        "Training windows:",
        len(X_train)
    )

    print(
        "Testing windows:",
        len(X_test)
    )

    print()

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    print("========================================")
    print(" DIAGNOSTIC RESULT")
    print("========================================")
    print()

    print(
        "Random window split accuracy:",
        round(
            accuracy * 100,
            2
        ),
        "%"
    )

    print()

    classes = sorted(
        set(y)
    )

    print("Classification Report:")
    print()

    print(
        classification_report(
            y_test,
            predictions,
            labels=classes,
            zero_division=0
        )
    )

    print("Confusion Matrix:")
    print()

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=classes
    )

    print(
        "Rows = Actual"
    )

    print(
        "Columns = Predicted"
    )

    print()

    print(classes)

    print(matrix)

    print()

    print("========================================")


if __name__ == "__main__":

    main()