# Sentinel Lending Risk

Sentinel is a real-time fraud detection prototype for digital lending. It combines deterministic rules, a supervised tabular model, anomaly evidence, explainable decisions, and an analyst review workflow.

## What is implemented

- React/TypeScript decision simulator and operations queue.
- FastAPI scoring and event-ingestion APIs.
- Rules for velocity, device reuse, identity mismatch, payment reuse, and risky networks.
- Random Forest supervised model and Isolation Forest anomaly model.
- Versioned feature schema and reproducible synthetic dataset.
- In-memory or SQLite persistence for events, decisions, cases, and feedback.
- Explainable reason codes and model-version audit metadata.
- Metrics endpoint and Docker Compose packaging.

The data is synthetic and the reported model metrics are prototype evidence only. They are not production fraud-performance claims.

## Quick start

### Backend

```powershell
python -m pip install -r backend/requirements.txt
python -m ml.data.generate_dataset
python -m ml.training.train_models
uvicorn backend.app.main:app --reload
```

API documentation: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

### Tests

```powershell
python -m pytest backend/tests -q
```

### Docker Compose

```powershell
docker compose up --build
```

Open `http://127.0.0.1:5173/` after both services become healthy.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/events` | Ingest an idempotent lending event |
| `POST` | `/api/v1/fraud/score` | Score a lending transaction |
| `GET` | `/api/v1/decisions/{decision_id}` | Retrieve audit metadata |
| `GET` | `/api/v1/cases` | List analyst cases |
| `PATCH` | `/api/v1/cases/{case_id}` | Save analyst outcome |
| `GET` | `/api/v1/metrics` | Return decision and case metrics |
| `GET` | `/health` | Service health check |

## Demo scenarios

1. Default signals produce `APPROVE`.
2. New device plus low identity match produces `MANUAL_REVIEW` and creates a case.
3. High network risk or linked entities produces `DECLINE` and creates a case.

## Responsible AI and limitations

The prototype uses synthetic data, human review for risk cases, stable reason codes, model/version audit fields, and no protected characteristics. Thresholds and metrics require validation on representative, governed production data. Online retraining is intentionally not enabled; analyst feedback is persisted for a future offline retraining workflow.