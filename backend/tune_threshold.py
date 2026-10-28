"""Compare fraud-classification thresholds for SentinelAI's public dataset baseline.

Run from the backend folder:
    python tune_threshold.py

This script recreates the same stratified train/test split and model pipeline used
by train_public_dataset.py. It does not modify or overwrite the saved model.
"""
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "raw" / "creditcard.csv"
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
TARGET = "Class"
THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80, 0.90]


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    missing = sorted(set(FEATURES + [TARGET]) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    X = df[FEATURES]
    y = df[TARGET].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = Pipeline([
        ("scale", StandardScaler()),
        ("model", LogisticRegression(
            class_weight="balanced", max_iter=2000,
            solver="lbfgs", random_state=42
        )),
    ])
    print("Training the same Logistic Regression baseline on the same split...")
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]

    print("\nThreshold | Precision | Recall | F1     | TP | FP   | FN")
    print("----------|-----------|--------|--------|----|------|---")
    rows = []
    for threshold in THRESHOLDS:
        predictions = (probabilities >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()
        precision = precision_score(y_test, predictions, zero_division=0)
        recall = recall_score(y_test, predictions, zero_division=0)
        f1 = f1_score(y_test, predictions, zero_division=0)
        rows.append({
            "threshold": threshold, "precision": precision, "recall": recall,
            "f1": f1, "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
        })
        print(
            f"{threshold:9.2f} | {precision:9.3f} | {recall:6.3f} | "
            f"{f1:6.3f} | {tp:2d} | {fp:4d} | {fn:2d}"
        )

    best = max(rows, key=lambda row: row["f1"])
    print("\nBest F1 among the tested thresholds:")
    print(
        f"threshold={best['threshold']:.2f}, precision={best['precision']:.3f}, "
        f"recall={best['recall']:.3f}, F1={best['f1']:.3f}, "
        f"FP={best['false_positive']}, FN={best['false_negative']}"
    )
    print("\nResearch only: choose thresholds based on business costs and validate on separate data.")
    print("Saved model and metrics files were not modified.")


if __name__ == "__main__":
    main()
