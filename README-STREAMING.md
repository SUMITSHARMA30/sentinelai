# SentinelAI Kafka + MongoDB streaming patch (Windows)

This patch adds a demo stream pipeline to the existing SentinelAI project. It replays rows from the ULB/Kaggle credit-card dataset into Kafka, scores each row with `backend/models/creditcard_baseline.joblib`, and stores results in MongoDB. It is real-time stream processing of a historical dataset, **not** a live bank/payment-gateway feed.

## 1. Copy files into your existing project

- Merge `docker-compose.yml` into the project root (or use it to replace the same compose file if it only contains Kafka and MongoDB).
- Copy `backend/streaming/producer.py` to `backend/streaming/producer.py`.
- Copy `backend/streaming/consumer.py` to `backend/streaming/consumer.py`.
- Copy `backend/app/stream_api.py` to `backend/app/stream_api.py`.

Do not overwrite your existing `backend/app/main.py`.

## 2. Install Python dependencies

From project root, with backend virtual environment activated:

```bat
cd /d D:\Downloads\sentinelai-starter\backend
.venv\Scripts\activate.bat
pip install kafka-python pymongo
```

Pandas and joblib should already be installed from model training.

## 3. Start infrastructure

From project root:

```bat
cd /d D:\Downloads\sentinelai-starter
docker compose up -d
docker compose ps
```

Both `sentinel-kafka` and `sentinel-mongodb` should be running.

## 4. Register the API router

Open `backend/app/main.py`. Add this import with the other imports:

```python
from app.stream_api import router as stream_router
```

After the existing `app = FastAPI(...)` declaration, add:

```python
app.include_router(stream_router)
```

Keep all existing routes and router registrations.

## 5. Run the backend

Terminal 1:

```bat
cd /d D:\Downloads\sentinelai-starter\backend
.venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --port 8000
```

## 6. Start the ML consumer

Terminal 2:

```bat
cd /d D:\Downloads\sentinelai-starter\backend
.venv\Scripts\activate.bat
python -m streaming.consumer
```

Keep this terminal open. It waits for Kafka events and prints each prediction.

## 7. Produce demo events

Terminal 3:

```bat
cd /d D:\Downloads\sentinelai-starter\backend
.venv\Scripts\activate.bat
python -m streaming.producer --limit 100 --delay 0.5
```

This default replays legitimate rows only. To include fraud examples in the replay:

```bat
python -m streaming.producer --limit 1000 --delay 0.2 --include-fraud
```

The model input contains only `Time`, `V1` through `V28`, and `Amount`. The dataset `Class` field is kept as `actual_class` metadata for demo evaluation and is never sent to the model.

## 8. Verify API endpoints

Open these URLs:

- `http://127.0.0.1:8000/stream/metrics`
- `http://127.0.0.1:8000/stream/transactions?limit=20`
- `http://127.0.0.1:8000/docs`

These endpoints expose the Kafka consumer's MongoDB results. They are separate from the existing simulated `/transactions` dashboard feed. Wire the frontend to `/stream/transactions` if you want to show these benchmark stream records in the UI; their feature schema differs from the original demo transaction schema.

## Troubleshooting

- `NoBrokersAvailable`: verify `docker compose ps` and `docker compose logs kafka`.
- Model not found: ensure `backend/models/creditcard_baseline.joblib` exists.
- Dataset not found: ensure `backend/data/raw/creditcard.csv` exists or pass `--csv "full\\path\\creditcard.csv"`.
- MongoDB unavailable: verify `docker compose logs mongodb` and port 27017 is free.
- If the API returns 404 for `/stream/metrics`, check the import and `app.include_router(stream_router)` in `main.py`.
