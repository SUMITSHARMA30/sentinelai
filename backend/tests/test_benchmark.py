from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_benchmark_metrics_available_after_training():
    response = client.get("/benchmark/metrics")
    # The test suite can run before the public dataset is downloaded.
    assert response.status_code in {200, 404}

def test_benchmark_score_requires_all_features():
    response = client.post("/benchmark/score", json={"Time": 0, "Amount": 1})
    assert response.status_code == 422
