from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from .config import MODEL_PATH

FEATURES = [
    "amount", "account_age_days", "transactions_last_hour",
    "distance_from_home_km", "device_new",
    "merchant_category", "channel", "country"
]
CATEGORIES = {
    "merchant_category": ["grocery", "electronics", "travel", "food", "fuel", "online", "other"],
    "channel": ["online", "pos", "mobile"],
    "country": ["IN", "US", "GB", "OTHER"]
}

def row_features(tx: dict) -> dict:
    country = tx.get("country", "IN")
    return {
        "amount": float(tx["amount"]),
        "account_age_days": int(tx.get("account_age_days", 365)),
        "transactions_last_hour": int(tx.get("transactions_last_hour", 1)),
        "distance_from_home_km": float(tx.get("distance_from_home_km", 2)),
        "device_new": int(bool(tx.get("device_new", False))),
        "merchant_category": tx.get("merchant_category", "online"),
        "channel": tx.get("channel", "online"),
        "country": country if country in CATEGORIES["country"][:-1] else "OTHER"
    }

def train_demo_model():
    rng = np.random.default_rng(42)
    n = 6000
    amount = rng.lognormal(5.0, 1.1, n).clip(10, 100000)
    age = rng.integers(0, 3000, n)
    velocity = rng.poisson(1.5, n)
    distance = rng.exponential(20, n).clip(0, 10000)
    new_device = rng.binomial(1, .18, n)
    merchant = rng.choice(CATEGORIES["merchant_category"], n)
    channel = rng.choice(CATEGORIES["channel"], n)
    country = rng.choice(["IN", "US", "GB", "OTHER"], n, p=[.8, .08, .07, .05])
    score = (
        (amount > 25000).astype(int) * 1.3
        + (velocity >= 5).astype(int) * 1.4
        + (distance > 250).astype(int) * 1.2
        + new_device * .8
        + (age < 14).astype(int) * .7
        + (country != "IN").astype(int) * .5
        + (channel == "online").astype(int) * .2
        + rng.normal(0, .7, n)
    )
    y = (score > 2.2).astype(int)
    X = {
        "amount": amount, "account_age_days": age,
        "transactions_last_hour": velocity, "distance_from_home_km": distance,
        "device_new": new_device, "merchant_category": merchant,
        "channel": channel, "country": country
    }
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    numeric = ["amount", "account_age_days", "transactions_last_hour", "distance_from_home_km", "device_new"]
    categorical = ["merchant_category", "channel", "country"]
    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical)
    ])
    pipeline = Pipeline([
        ("prep", prep),
        ("model", RandomForestClassifier(n_estimators=120, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1))
    ])
    import pandas as pd
    pipeline.fit(pd.DataFrame(X), y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    return pipeline

def load_model():
    if not MODEL_PATH.exists():
        return train_demo_model()
    return joblib.load(MODEL_PATH)

def predict(tx: dict) -> tuple[float, list[str]]:
    import pandas as pd
    model = load_model()
    row = row_features(tx)
    probability = float(model.predict_proba(pd.DataFrame([row]))[0][1])
    reasons = []
    if row["amount"] > 25000: reasons.append("High transaction amount")
    if row["transactions_last_hour"] >= 5: reasons.append("Unusually high transaction velocity")
    if row["distance_from_home_km"] > 250: reasons.append("Large distance from usual location")
    if row["device_new"]: reasons.append("New device")
    if row["account_age_days"] < 14: reasons.append("Recently created account")
    if row["country"] != "IN": reasons.append("Transaction country differs from primary market")
    if not reasons: reasons.append("No obvious rule-based risk signal")
    return probability, reasons
