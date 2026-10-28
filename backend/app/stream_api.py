"""Read-only API endpoints for MongoDB-backed Kafka scoring results."""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient

router = APIRouter(prefix="/stream", tags=["Kafka stream"])


def get_collection():
    client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        return client, client["sentinelai"]["stream_transactions"]
    except Exception:
        client.close()
        raise


@router.get("/transactions")
def stream_transactions(limit: int = Query(100, ge=1, le=500)):
    client = None
    try:
        client, collection = get_collection()
        rows = list(collection.find({}, {"_id": 0}).sort("processed_at", -1).limit(limit))
        for row in rows:
            if isinstance(row.get("processed_at"), datetime):
                row["processed_at"] = row["processed_at"].isoformat()
        return {"count": len(rows), "items": rows}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Stream storage unavailable: {exc}") from exc
    finally:
        if client:
            client.close()


@router.get("/metrics")
def stream_metrics():
    client = None
    try:
        client, collection = get_collection()
        total = collection.count_documents({})
        fraud = collection.count_documents({"prediction": "fraud_review"})
        legitimate = collection.count_documents({"prediction": "legitimate"})
        latest = collection.find_one({}, {"_id": 0, "processed_at": 1}, sort=[("processed_at", -1)])
        if latest and isinstance(latest.get("processed_at"), datetime):
            latest["processed_at"] = latest["processed_at"].isoformat()
        return {"total_processed": total, "fraud_review": fraud, "legitimate": legitimate,
                "fraud_review_rate": round(fraud / total, 4) if total else 0,
                "latest_processed_at": latest.get("processed_at") if latest else None,
                "source_note": "Historical dataset replay for demonstration; not a live payment feed."}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Stream storage unavailable: {exc}") from exc
    finally:
        if client:
            client.close()
