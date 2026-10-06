from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier
)

from sklearn.metrics import (
    accuracy_score,
    f1_score
)

from sklearn.model_selection import (
    StratifiedGroupKFold
)

from sklearn.pipeline import Pipeline

from sklearn.preprocessing import (
    StandardScaler
)

from sklearn.svm import SVC


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

DATA_PATH = (
    PROJECT_ROOT
    / "ai"
    / "dataset"
    / "processed"
    / "train.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "ai"
    / "model"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "ai"
    / "dataset"
    / "evaluation"
)

RANDOM_SEED = 42

META_COLUMNS = [
    "recording_id",
    "label",
    "window_start"
]


def load_training_data():

    if not DATA_PATH.exists():

        raise FileNotFoundError(
            f"{DATA_PATH} not found. "
            f"Run preprocess.py first."
        )

    df = pd.read_csv(
        DATA_PATH
    )

    feature_columns = [
        column
        for column in df.columns
        if column not in META_COLUMNS
    ]

    X = df[
        feature_columns
    ].astype(float)

    y = df[
        "label"
    ].astype(str)

    groups = df[
        "recording_id"
    ].astype(str)

    return (
        X,
        y,
        groups,
        feature_columns
    )


def create_models():

    return {

        "Random Forest":
            RandomForestClassifier(
                n_estimators=400,
                max_features="sqrt",
                class_weight="balanced",
                random_state=RANDOM_SEED,
                n_jobs=-1
            ),

        "SVM RBF":
            Pipeline([
                (
                    "scaler",
                    StandardScaler()
                ),

                (
                    "model",
                    SVC(
                        kernel="rbf",
                        C=10.0,
                        gamma="scale",
                        class_weight="balanced",
                        probability=True,
                        random_state=RANDOM_SEED
                    )
                )
            ])
    }


def run_grouped_cv(
    model,
    X,
    y,
    groups
):

    group_counts = (
        pd.DataFrame({
            "label": y,
            "group": groups
        })
        .drop_duplicates()
        .groupby("label")["group"]
        .nunique()
    )

    minimum_groups = int(
        group_counts.min()
    )

    if minimum_groups < 2:

        raise RuntimeError(
            "At least two training recordings "
            "per class are required."
        )

    n_splits = min(
        5,
        minimum_groups
    )

    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=RANDOM_SEED
    )

    fold_results = []

    for fold, (
        train_index,
        validation_index
    ) in enumerate(
        splitter.split(
            X,
            y,
            groups
        ),
        start=1
    ):

        X_train = X.iloc[
            train_index
        ]

        X_validation = X.iloc[
            validation_index
        ]

        y_train = y.iloc[
            train_index
        ]

        y_validation = y.iloc[
            validation_index
        ]

        model.fit(
            X_train,
            y_train
        )

        predictions = model.predict(
            X_validation
        )

        accuracy = accuracy_score(
            y_validation,
            predictions
        )

        macro_f1 = f1_score(
            y_validation,
            predictions,
            average="macro",
            zero_division=0
        )

        fold_results.append({
            "model": "",
            "fold": fold,
            "accuracy": accuracy,
            "macro_f1": macro_f1
        })

        print(
            f"      Fold {fold}: "
            f"accuracy="
            f"{accuracy * 100:.2f}% | "
            f"macro-F1="
            f"{macro_f1 * 100:.2f}%"
        )

    return fold_results


def main():

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    (
        X,
        y,
        groups,
        feature_columns
    ) = load_training_data()

    print("=" * 70)
    print("GLOVECARE AI - MODEL TRAINING")
    print("=" * 70)

    print(
        f"Training windows : "
        f"{len(X)}"
    )

    print(
        f"Features         : "
        f"{len(feature_columns)}"
    )

    print(
        f"Recordings       : "
        f"{groups.nunique()}"
    )

    print(
        f"Classes          : "
        f"{sorted(y.unique())}"
    )

    print()
    print(
        "Training/validation uses only TRAIN recordings."
    )

    print(
        "The TEST set is not touched here."
    )

    print()

    models = create_models()

    all_results = []

    summary = []

    for model_name, model in models.items():

        print("-" * 70)
        print(
            f"MODEL: {model_name}"
        )
        print("-" * 70)

        fold_results = run_grouped_cv(
            model,
            X,
            y,
            groups
        )

        for row in fold_results:
            row["model"] = model_name

        all_results.extend(
            fold_results
        )

        accuracies = [
            row["accuracy"]
            for row in fold_results
        ]

        f1_scores = [
            row["macro_f1"]
            for row in fold_results
        ]

        mean_accuracy = float(
            np.mean(accuracies)
        )

        std_accuracy = float(
            np.std(accuracies)
        )

        mean_f1 = float(
            np.mean(f1_scores)
        )

        std_f1 = float(
            np.std(f1_scores)
        )

        summary.append({
            "model":
                model_name,

            "mean_accuracy":
                mean_accuracy,

            "std_accuracy":
                std_accuracy,

            "mean_macro_f1":
                mean_f1,

            "std_macro_f1":
                std_f1
        })

        print(
            f"Mean accuracy: "
            f"{mean_accuracy * 100:.2f}% "
            f"+/- "
            f"{std_accuracy * 100:.2f}%"
        )

        print(
            f"Mean macro-F1: "
            f"{mean_f1 * 100:.2f}% "
            f"+/- "
            f"{std_f1 * 100:.2f}%"
        )

        print()

    summary_df = pd.DataFrame(
        summary
    )

    best_row = (
        summary_df
        .sort_values(
            [
                "mean_macro_f1",
                "mean_accuracy"
            ],
            ascending=False
        )
        .iloc[0]
    )

    best_name = best_row[
        "model"
    ]

    best_model = models[
        best_name
    ]

    print("=" * 70)
    print(
        f"SELECTED MODEL: {best_name}"
    )
    print("=" * 70)

    print(
        "Fitting selected model "
        "on ALL training recordings..."
    )

    best_model.fit(
        X,
        y
    )

    model_package = {

        "model":
            best_model,

        "feature_columns":
            feature_columns,

        "classes":
            sorted(
                y.unique().tolist()
            ),

        "window_size":
            40,

        "model_name":
            best_name,

        "version":
            "GloveCare-2026-v2"
    }

    model_path = (
        MODEL_DIR
        / "glovecare_model.pkl"
    )

    joblib.dump(
        model_package,
        model_path
    )

    summary_df.to_csv(
        RESULTS_DIR
        / "training_model_comparison.csv",
        index=False
    )

    pd.DataFrame(
        all_results
    ).to_csv(
        RESULTS_DIR
        / "training_cv_results.csv",
        index=False
    )

    with (
        RESULTS_DIR
        / "training_summary.json"
    ).open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "selected_model":
                    best_name,

                "training_windows":
                    len(X),

                "training_recordings":
                    int(groups.nunique()),

                "feature_count":
                    len(feature_columns),

                "classes":
                    sorted(
                        y.unique().tolist()
                    ),

                "cv_mean_accuracy":
                    float(
                        best_row[
                            "mean_accuracy"
                        ]
                    ),

                "cv_std_accuracy":
                    float(
                        best_row[
                            "std_accuracy"
                        ]
                    ),

                "cv_mean_macro_f1":
                    float(
                        best_row[
                            "mean_macro_f1"
                        ]
                    ),

                "cv_std_macro_f1":
                    float(
                        best_row[
                            "std_macro_f1"
                        ]
                    )
            },
            file,
            indent=4
        )

    print()
    print(
        f"Model saved: "
        f"{model_path}"
    )

    print(
        "Training complete."
    )

    print()
    print(
        "Now run test_model.py "
        "for FINAL TEST evaluation."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()