
from pathlib import Path
import json
import os
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import Field, create_model

router = APIRouter(prefix="/benchmark", tags=["Public-dataset benchmark"])

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BACKEND_DIR / "models" / "creditcard_baseline.joblib"
METRICS_PATH = BACKEND_DIR / "models" / "creditcard_baseline_metrics.json"
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]

DEFAULT_THRESHOLD = float(os.getenv("BENCHMARK_THRESHOLD", "0.5"))

fields = {
    "Time": (float, Field(ge=0)),
    **{
        f"V{i}": (float, Field(description=f"Anonymized PCA feature V{i}"))
        for i in range(1, 29)
    },
    "Amount": (float, Field(ge=0)),
}

BenchmarkTransactionIn = create_model("BenchmarkTransactionIn", **fields)


@router.get("/metrics")
def benchmark_metrics():
    if not METRICS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Benchmark metrics not found. Run python train_public_dataset.py first."
        )

    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


@router.post("/score")
def score_benchmark_transaction(
    payload: BenchmarkTransactionIn,
    threshold: float = Query(DEFAULT_THRESHOLD, ge=0, le=1)
):
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Benchmark model not found. Run python train_public_dataset.py first."
        )

    try:
        artifact = joblib.load(MODEL_PATH)
        pipeline = artifact["pipeline"]
        expected_features = artifact["features"]

        if expected_features != FEATURES:
            raise ValueError("Feature schema mismatch in saved model artifact.")

        row = pd.DataFrame([payload.model_dump()], columns=FEATURES)
        probability = float(pipeline.predict_proba(row)[0][1])

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark scoring failed: {exc}"
        ) from exc

    prediction = int(probability >= threshold)

    return {
        "model_version": artifact.get("model_version", "unknown"),
        "fraud_probability": round(probability, 6),
        "threshold": threshold,
        "prediction": "fraud_review" if prediction else "legitimate",
        "warning": (
            "Research benchmark only. Threshold is configurable; "
            "not for real payment authorization."
        )
    }
