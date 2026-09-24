# Fraud Detection Backend

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

## Run the API

```powershell
python -m ml.data.generate_dataset
python -m ml.training.train_models
uvicorn backend.app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI documentation.

## Persistent local storage

The default test and development mode uses in-memory storage. To persist events
and decisions in a local SQLite database, set these variables before starting:

```powershell
$env:FRAUD_STORE = "sqlite"
$env:FRAUD_DB_PATH = "fraud_detection.db"
uvicorn app.main:app --reload
```

The storage boundary is ready to be replaced with PostgreSQL without changing
the API or fraud decision logic.

## Run tests

```powershell
pytest
```