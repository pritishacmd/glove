from pathlib import Path

import json
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EVALUATION_DIR = (
    PROJECT_ROOT
    / "ai"
    / "dataset"
    / "evaluation"
)


def evaluate_predictions(
    y_true,
    y_pred,
    class_names
):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    balanced_accuracy = balanced_accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        labels=class_names,
        average="weighted",
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        labels=class_names,
        average="weighted",
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        labels=class_names,
        average="weighted",
        zero_division=0
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=class_names
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=class_names,
        target_names=class_names,
        zero_division=0
    )

    per_class_report = classification_report(
        y_true,
        y_pred,
        labels=class_names,
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    results = {
        "accuracy": float(accuracy),
        "balanced_accuracy": float(balanced_accuracy),
        "precision_weighted": float(precision),
        "recall_weighted": float(recall),
        "f1_weighted": float(f1),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "per_class_report": per_class_report
    }

    return results


def save_evaluation(
    results,
    class_names,
    prefix="test"
):

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    json_path = (
        EVALUATION_DIR
        / f"{prefix}_evaluation.json"
    )

    confusion_path = (
        EVALUATION_DIR
        / f"{prefix}_confusion_matrix.csv"
    )

    metrics_path = (
        EVALUATION_DIR
        / f"{prefix}_metrics.csv"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    confusion_matrix_data = np.asarray(
        results["confusion_matrix"]
    )

    import pandas as pd

    confusion_df = pd.DataFrame(
        confusion_matrix_data,
        index=class_names,
        columns=class_names
    )

    confusion_df.index.name = "Actual"

    confusion_df.to_csv(
        confusion_path
    )

    metrics_df = pd.DataFrame(
        [
            {
                "metric": "Accuracy",
                "value": results["accuracy"]
            },
            {
                "metric": "Balanced Accuracy",
                "value": results["balanced_accuracy"]
            },
            {
                "metric": "Weighted Precision",
                "value": results["precision_weighted"]
            },
            {
                "metric": "Weighted Recall",
                "value": results["recall_weighted"]
            },
            {
                "metric": "Weighted F1 Score",
                "value": results["f1_weighted"]
            }
        ]
    )

    metrics_df.to_csv(
        metrics_path,
        index=False
    )

    print()
    print(
        f"Evaluation JSON saved: "
        f"{json_path}"
    )

    print(
        f"Confusion matrix saved: "
        f"{confusion_path}"
    )

    print(
        f"Metrics saved: "
        f"{metrics_path}"
    )


def print_evaluation(
    results
):

    print()
    print("=" * 70)
    print("FINAL TEST EVALUATION")
    print("=" * 70)

    print(
        f"Accuracy            : "
        f"{results['accuracy'] * 100:.2f}%"
    )

    print(
        f"Balanced Accuracy   : "
        f"{results['balanced_accuracy'] * 100:.2f}%"
    )

    print(
        f"Weighted Precision  : "
        f"{results['precision_weighted'] * 100:.2f}%"
    )

    print(
        f"Weighted Recall     : "
        f"{results['recall_weighted'] * 100:.2f}%"
    )

    print(
        f"Weighted F1 Score   : "
        f"{results['f1_weighted'] * 100:.2f}%"
    )

    print()
    print("Classification Report")
    print("-" * 70)

    print(
        results["classification_report"]
    )

    print()
    print("Confusion Matrix")
    print("-" * 70)

    print(
        np.array(
            results["confusion_matrix"]
        )
    )

    print("=" * 70)