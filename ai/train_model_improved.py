import os
import csv
import joblib

from sklearn.ensemble import RandomForestClassifier
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
    "processed_windows_improved.csv"
)

MODEL_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "ai",
    "model"
)

MODEL_FILE = os.path.join(
    MODEL_FOLDER,
    "random_forest_model_improved.pkl"
)


def read_dataset():

    features = []
    labels = []
    recording_ids = []

    with open(
        PROCESSED_FILE,
        "r",
        newline=""
    ) as file:

        reader = csv.reader(file)

        header = next(reader)

        for row in reader:

            if len(row) < 4:
                continue

            recording_id = row[0]
            label = row[2]

            try:

                values = []

                for value in row[3:]:

                    values.append(
                        float(value)
                    )

            except ValueError:

                continue

            recording_ids.append(
                recording_id
            )

            labels.append(
                label
            )

            features.append(
                values
            )

    return (
        features,
        labels,
        recording_ids
    )


def main():

    print()
    print("========================================")
    print("   GLOVECARE IMPROVED MODEL TRAINING")
    print("========================================")
    print()

    os.makedirs(
        MODEL_FOLDER,
        exist_ok=True
    )

    X, y, recording_ids = read_dataset()

    print(
        "Total windows:",
        len(X)
    )

    print(
        "Features per window:",
        len(X[0])
    )

    print()

    classes = sorted(
        set(y)
    )

    print("Classes:")

    for label in classes:

        count = y.count(
            label
        )

        print(
            " ",
            label,
            "->",
            count,
            "windows"
        )

    print()

    print("========================================")
    print(" RECORDING-LEVEL TESTING")
    print("========================================")
    print()

    all_actual = []
    all_predicted = []

    for test_number in [
        "1",
        "2",
        "3"
    ]:

        print(
            "Testing recording:",
            test_number
        )

        X_train = []
        y_train = []

        X_test = []
        y_test = []

        for i in range(
            len(X)
        ):

            recording_number = (
                recording_ids[i]
                .rsplit("_", 1)[-1]
            )

            if recording_number == test_number:

                X_test.append(
                    X[i]
                )

                y_test.append(
                    y[i]
                )

            else:

                X_train.append(
                    X[i]
                )

                y_train.append(
                    y[i]
                )

        print(
            "  Training windows:",
            len(X_train)
        )

        print(
            "  Testing windows:",
            len(X_test)
        )

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

        print(
            "  Accuracy:",
            round(
                accuracy * 100,
                2
            ),
            "%"
        )

        all_actual.extend(
            y_test
        )

        all_predicted.extend(
            predictions
        )

        print()

    print("========================================")
    print(" OVERALL CROSS-RECORDING RESULTS")
    print("========================================")
    print()

    overall_accuracy = accuracy_score(
        all_actual,
        all_predicted
    )

    print(
        "Overall Accuracy:",
        round(
            overall_accuracy * 100,
            2
        ),
        "%"
    )

    print()

    print("Classification Report:")
    print()

    print(
        classification_report(
            all_actual,
            all_predicted,
            labels=classes,
            zero_division=0
        )
    )

    print("Confusion Matrix:")
    print()

    matrix = confusion_matrix(
        all_actual,
        all_predicted,
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
    print(" TRAINING FINAL IMPROVED MODEL")
    print("========================================")
    print()

    final_model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced"
    )

    final_model.fit(
        X,
        y
    )

    model_data = {
        "model": final_model,
        "feature_count": len(X[0]),
        "classes": classes
    }

    joblib.dump(
        model_data,
        MODEL_FILE
    )

    print(
        "Final improved model trained using all data."
    )

    print()

    print(
        "Model saved to:"
    )

    print(
        MODEL_FILE
    )

    print()

    print("========================================")
    print("       IMPROVED TRAINING COMPLETE")
    print("========================================")
    print()


if __name__ == "__main__":

    main()