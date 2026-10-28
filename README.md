# SentinelAI — Real-Time Fraud Detection Starter

An educational fintech fraud-detection prototype built with FastAPI, scikit-learn, MongoDB, and Next.js.
This starter is a safe local MVP: transactions are synthetic, and predictions are not proof of fraud.

## Architecture (starter)
Browser UI -> FastAPI -> ML risk scorer -> MongoDB (optional; JSONL fallback)
Later phases add Kafka ingestion, model monitoring, authentication, and deployment.

## Prerequisites
- Python 3.11+
- Node.js 20+
- Git
- MongoDB locally or a MongoDB Atlas connection string (optional)

## 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python train_model.py
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs and http://localhost:8000/health.

If using PowerShell, `copy .env.example .env` works. If you use Command Prompt, it also works.

## 2. Frontend
Open a second terminal:
```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```
Open http://localhost:3000.

## 3. Try it
- Click **Generate transaction** in the UI.
- Use `/docs` to try `POST /transactions`.
- `GET /transactions` lists recent records.
- `GET /metrics` returns summary counts.

## Environment
`MONGODB_URI` is optional. If omitted, the backend stores records in `backend/data/transactions.jsonl` for local development.
Never commit secrets or real cardholder data.

## Important limitations
- The included model is a demo model trained on generated data so the application can run immediately.
- It is not validated for real payment decisions.
- A later phase will replace the demo data with a public anonymized dataset and add proper evaluation, time-aware validation, drift monitoring, and explainability.
- No real payments are processed, blocked, or authorized.
