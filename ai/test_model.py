from pathlib import Path

import joblib
import pandas as pd

from evaluate_model import (
    evaluate_predictions,
    save_evaluation,
    print_evaluation
)


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

TEST_PATH = (
    PROJECT_ROOT
    / "ai"
    / "dataset"
    / "processed"
    / "test.csv"
)

MODEL_PATH = (
    PROJECT_ROOT
    / "ai"
    / "model"
    / "glovecare_model.pkl"
)


def main():

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"{MODEL_PATH} not found. "
            f"Run train_model.py first."
        )

    if not TEST_PATH.exists():

        raise FileNotFoundError(
            f"{TEST_PATH} not found. "
            f"Run preprocess.py first."
        )

    package = joblib.load(
        MODEL_PATH
    )

    model = package[
        "model"
    ]

    feature_columns = package[
        "feature_columns"
    ]

    class_names = package[
        "classes"
    ]

    test_df = pd.read_csv(
        TEST_PATH
    )

    missing = [
        column
        for column in feature_columns
        if column not in test_df.columns
    ]

    if missing:

        raise RuntimeError(
            f"Test dataset is missing "
            f"{len(missing)} features."
        )

    X_test = test_df[
        feature_columns
    ].astype(float)

    y_test = test_df[
        "label"
    ].astype(str)

    print("=" * 70)
    print("GLOVECARE AI - FINAL TESTING")
    print("=" * 70)

    print(
        f"Test windows : "
        f"{len(X_test)}"
    )

    print(
        f"Test classes : "
        f"{class_names}"
    )

    print()

    print(
        "IMPORTANT: This script does NOT train "
        "or fit the model."
    )

    print(
        "The saved model is evaluated on "
        "untouched TEST recordings."
    )

    print()

    predictions = model.predict(
        X_test
    )

    output = test_df[
        [
            "recording_id",
            "label",
            "window_start"
        ]
    ].copy()

    output[
        "prediction"
    ] = predictions

    if hasattr(
        model,
        "predict_proba"
    ):

        probabilities = (
            model.predict_proba(
                X_test
            )
        )

        output[
            "confidence"
        ] = probabilities.max(
            axis=1
        )

    else:

        output[
            "confidence"
        ] = 0.0

    output_path = (
        PROJECT_ROOT
        / "ai"
        / "dataset"
        / "evaluation"
        / "test_predictions.csv"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.to_csv(
        output_path,
        index=False
    )

    results = evaluate_predictions(
        y_test,
        predictions,
        class_names
    )

    save_evaluation(
        results,
        class_names,
        prefix="test"
    )

    print_evaluation(
        results
    )

    print()

    print(
        f"Predictions saved: "
        f"{output_path}"
    )

    print(
        "Evaluation files saved in: "
        f"{output_path.parent}"
    )


if __name__ == "__main__":
    main()