"""Replay public credit-card dataset rows into Kafka as a demo transaction stream."""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "raw" / "creditcard.csv"
TOPIC = "transactions"
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between events")
    parser.add_argument("--limit", type=int, default=100, help="Number of rows to replay; 0 means all")
    parser.add_argument("--include-fraud", action="store_true", help="Include fraud examples in replay")
    args = parser.parse_args()

    path = Path(args.csv)
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}\nPut creditcard.csv in backend/data/raw/ or pass --csv.")

    df = pd.read_csv(path)
    if "Class" not in df.columns or any(c not in df.columns for c in FEATURES):
        raise SystemExit("CSV must contain Time, V1..V28, Amount, and Class columns.")
    if not args.include_fraud:
        # Preserve the dataset order but include a few fraud rows later via --include-fraud if desired.
        df = df[df["Class"] == 0]
    if args.limit > 0:
        df = df.head(args.limit)

    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        retries=5,
    )
    try:
        for index, row in df.iterrows():
            event = {feature: float(row[feature]) for feature in FEATURES}
            event["event_id"] = f"dataset-row-{index}"
            event["actual_class"] = int(row["Class"])  # evaluation metadata; never passed as model input
            event["source"] = "historical_public_dataset_replay"
            producer.send(TOPIC, value=event).get(timeout=15)
            print(f"Sent {event['event_id']} actual_class={event['actual_class']}")
            time.sleep(max(0.0, args.delay))
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
