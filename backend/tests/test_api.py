from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_transaction():
    response = client.post("/transactions", json={
        "amount": 500,
        "currency": "INR",
        "merchant_category": "grocery",
        "channel": "pos",
        "country": "IN",
        "account_age_days": 900,
        "transactions_last_hour": 1,
        "distance_from_home_km": 2,
        "device_new": False
    })
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["fraud_probability"] <= 1
    assert body["risk_level"] in {"low", "medium", "high"}
    assert body["transaction_id"]
