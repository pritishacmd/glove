import os
import csv
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

PROJECT_FOLDER = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_FILE = os.path.join(
    PROJECT_FOLDER,
    "ai",
    "dataset",
    "processed_windows.csv"
)

MODEL_FOLDER = os.path.join(
    PROJECT_FOLDER,
    "ai",
    "model"
)

MODEL_FILE = os.path.join(
    MODEL_FOLDER,
    "glovecare_model.pkl"
)


def load_data():

    X = []
    y = []
    groups = []

    with open(DATA_FILE, "r", newline="") as file:

        reader = csv.DictReader(file)

        feature_columns = []

        for column in reader.fieldnames:
            if column not in ["label", "recording_id"]:
                feature_columns.append(column)

        for row in reader:

            features = []

            for column in feature_columns:
                features.append(float(row[column]))

            X.append(features)
            y.append(row["label"])
            groups.append(row["recording_id"])

    return X, y, groups


print()
print("========================================")
print("       GLOVECARE AI MODEL TRAINING")
print("========================================")
print()

X, y, groups = load_data()

print("Total windows:", len(X))
print("Features per window:", len(X[0]))
print("Recordings:", len(set(groups)))
print()

print("Training Random Forest...")

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced"
)

group_kfold = GroupKFold(n_splits=6)

scores = cross_val_score(
    model,
    X,
    y,
    groups=groups,
    cv=group_kfold,
    scoring="accuracy"
)

print()
print("Recording-level cross-validation results:")
print()

for i in range(len(scores)):
    print(
        "Fold",
        i + 1,
        "accuracy:",
        f"{scores[i] * 100:.2f}%"
    )

print()
print(
    "Average accuracy:",
    f"{scores.mean() * 100:.2f}%"
)

print(
    "Standard deviation:",
    f"{scores.std() * 100:.2f}%"
)

print()
print("Training final model using all recordings...")

model.fit(X, y)

os.makedirs(
    MODEL_FOLDER,
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_FILE
)

print()
print("========================================")
print("          MODEL SAVED")
print("========================================")
print()

print("Model file:")
print(MODEL_FILE)

print()
print("DONE.")
print()