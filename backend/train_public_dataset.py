"""
Train and evaluate a baseline on the public ULB credit-card fraud dataset.

Expected input: backend/data/raw/creditcard.csv
Expected columns: Time, V1..V28, Amount, Class (Class: 1=fraud, 0=legitimate)

This is a benchmark pipeline, separate from the synthetic-feature API model.
The public dataset's PCA features are not interchangeable with API fields like
device_new or transactions_last_hour.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = BASE_DIR / "data" / "raw" / "creditcard.csv"
MODEL_PATH = BASE_DIR / "models" / "creditcard_baseline.joblib"
METRICS_PATH = BASE_DIR / "models" / "creditcard_baseline_metrics.json"
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
TARGET = "Class"


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Download creditcard.csv and place it in backend/data/raw/."
        )
    df = pd.read_csv(path)
    required = set(FEATURES + [TARGET])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Dataset is empty.")
    if df[FEATURES + [TARGET]].isna().any().any():
        raise ValueError("Dataset contains missing values in required columns.")
    labels = set(df[TARGET].unique())
    if not labels.issubset({0, 1}) or len(labels) != 2:
        raise ValueError(f"Expected both binary labels 0 and 1; found {labels}.")
    return df


def evaluate_predictions(y_true, probabilities, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    cm = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "threshold": threshold,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "average_precision_pr_auc": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "confusion_matrix": {
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1]),
        },
        "classification_report": classification_report(
            y_true, predictions, labels=[0, 1],
            target_names=["legitimate", "fraud"],
            output_dict=True, zero_division=0
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to creditcard.csv")
    parser.add_argument("--threshold", type=float, default=0.5, help="Probability threshold for classification")
    args = parser.parse_args()
    if not 0 < args.threshold < 1:
        parser.error("--threshold must be between 0 and 1")

    df = load_dataset(args.data)
    X = df[FEATURES]
    y = df[TARGET].astype(int)

    # Stratification preserves the rare fraud class in both sets.
    # This is a reproducible baseline split, not a production time-based validation.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scale", StandardScaler()),
        ("model", LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            solver="lbfgs",
            random_state=42
        )),
    ])
    print(f"Rows: {len(df):,} | fraud: {int(y.sum()):,} ({y.mean():.4%})")
    print(f"Training on {len(X_train):,} rows; evaluating on {len(X_test):,} rows.")
    print("Training LogisticRegression(class_weight='balanced')...")
    pipeline.fit(X_train, y_train)

    probabilities = pipeline.predict_proba(X_test)[:, 1]
    metrics = evaluate_predictions(y_test.to_numpy(), probabilities, args.threshold)
    metrics.update({
        "model_name": "LogisticRegression",
        "dataset": "ULB/Kaggle Credit Card Fraud Detection",
        "dataset_rows": int(len(df)),
        "fraud_rows": int(y.sum()),
        "fraud_prevalence": float(y.mean()),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "features": FEATURES,
        "split": "stratified random 80/20; random_state=42",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "Research baseline only. Dataset covers two days in 2013 and uses "
            "PCA-transformed features; metrics do not establish production performance."
        ),
    })

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "features": FEATURES, "model_version": "creditcard-logreg-v1"}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\nHeld-out test metrics")
    for key in ("precision", "recall", "f1", "average_precision_pr_auc", "roc_auc"):
        print(f"{key}: {metrics[key]:.6f}")
    print("Confusion matrix:", metrics["confusion_matrix"])
    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"Metrics saved to: {METRICS_PATH}")
    print("\nReminder: this model expects Time, V1..V28, Amount—not the demo API feature schema.")


if __name__ == "__main__":
    main()
