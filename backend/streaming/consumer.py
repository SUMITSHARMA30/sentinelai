"""Consume Kafka transaction events, score with the trained model, and persist to MongoDB."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from kafka import KafkaConsumer
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
MODEL_PATH = BACKEND / "models" / "creditcard_baseline.joblib"
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
THRESHOLD = float(os.getenv("BENCHMARK_THRESHOLD", "0.5"))


def main():
    if not MODEL_PATH.exists():
        raise SystemExit(f"Model not found: {MODEL_PATH}. Train it first with python train_public_dataset.py")

    artifact = joblib.load(MODEL_PATH)
    pipeline = artifact["pipeline"]
    if artifact.get("features") != FEATURES:
        raise SystemExit("Saved model feature schema does not match the consumer schema.")

    mongo = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000)
    mongo.admin.command("ping")
    collection = mongo["sentinelai"]["stream_transactions"]
    collection.create_index("event_id", unique=True)

    consumer = KafkaConsumer(
        "transactions",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        group_id="sentinelai-ml-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    print(f"Consumer ready. Threshold={THRESHOLD}. Waiting for Kafka events...")
    try:
        for message in consumer:
            event = message.value
            try:
                row = pd.DataFrame([{feature: float(event[feature]) for feature in FEATURES}], columns=FEATURES)
                probability = float(pipeline.predict_proba(row)[0][1])
                result = {
                    "event_id": str(event.get("event_id", f"kafka-{message.partition}-{message.offset}")),
                    "source": event.get("source", "kafka"),
                    "fraud_probability": probability,
                    "threshold": THRESHOLD,
                    "prediction": "fraud_review" if probability >= THRESHOLD else "legitimate",
                    "actual_class": int(event["actual_class"]) if event.get("actual_class") is not None else None,
                    "model_version": artifact.get("model_version", "unknown"),
                    "processed_at": datetime.now(timezone.utc),
                }
                collection.update_one({"event_id": result["event_id"]}, {"$set": result}, upsert=True)
                print(f"Scored {result['event_id']}: {result['prediction']} p={probability:.4f}")
            except Exception as exc:
                print(f"Skipping invalid event at offset {message.offset}: {exc}")
    finally:
        consumer.close()
        mongo.close()


if __name__ == "__main__":
    main()
