from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.stream_api import router as stream_router

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .config import CORS_ORIGINS
from .schemas import TransactionIn
from .model import predict
from . import store
from .benchmark import router as benchmark_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="SentinelAI Fraud Detection API", version="0.2.0", lifespan=lifespan)
app.include_router(stream_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in CORS_ORIGINS if x.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(benchmark_router)

def assess(tx: TransactionIn) -> dict:
    raw = tx.model_dump()
    probability, reasons = predict(raw)
    risk = "high" if probability >= .70 else "medium" if probability >= .35 else "low"
    status = "blocked" if risk == "high" else "review" if risk == "medium" else "approved"
    record = {
        **raw,
        "transaction_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fraud_probability": round(probability, 4),
        "risk_level": risk,
        "model_version": "demo-v1",
        "status": status,
        "analyst_label": "unknown",
        "reasons": reasons,
    }
    store.insert(record)
    return record

@app.get("/health")
def health():
    return {"status": "ok", "service": "sentinelai-api", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/transactions")
def create_transaction(tx: TransactionIn):
    return assess(tx)

@app.get("/transactions")
def list_transactions(limit: int = Query(default=100, ge=1, le=500), risk: str | None = None):
    records = store.all_records(limit=limit)
    if risk in {"low", "medium", "high"}:
        records = [r for r in records if r.get("risk_level") == risk]
    return {"items": records, "count": len(records)}

@app.get("/metrics")
def metrics():
    records = store.all_records(limit=100000)
    return {
        "total_transactions": len(records),
        "high_risk": sum(r.get("risk_level") == "high" for r in records),
        "medium_risk": sum(r.get("risk_level") == "medium" for r in records),
        "low_risk": sum(r.get("risk_level") == "low" for r in records),
        "confirmed_fraud": sum(r.get("analyst_label") == "confirmed_fraud" for r in records),
        "model_version": "demo-v1"
    }

@app.patch("/transactions/{transaction_id}/label")
def label_transaction(transaction_id: str, label: str):
    if label not in {"confirmed_fraud", "legitimate", "unknown"}:
        raise HTTPException(status_code=422, detail="label must be confirmed_fraud, legitimate, or unknown")
    if not store.update_label(transaction_id, label):
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"transaction_id": transaction_id, "analyst_label": label}
