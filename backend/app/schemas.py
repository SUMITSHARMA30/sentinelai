from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field
import uuid

class TransactionIn(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    merchant_category: Literal["grocery", "electronics", "travel", "food", "fuel", "online", "other"] = "online"
    channel: Literal["online", "pos", "mobile"] = "online"
    country: str = Field(default="IN", min_length=2, max_length=2)
    account_age_days: int = Field(default=365, ge=0, le=50000)
    transactions_last_hour: int = Field(default=1, ge=0, le=1000)
    distance_from_home_km: float = Field(default=2, ge=0, le=50000)
    device_new: bool = False

class TransactionRecord(TransactionIn):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fraud_probability: float
    risk_level: Literal["low", "medium", "high"]
    model_version: str = "demo-v1"
    status: Literal["approved", "review", "blocked"] = "approved"
    analyst_label: Literal["unknown", "confirmed_fraud", "legitimate"] = "unknown"
    reasons: list[str] = []
