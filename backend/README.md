# Fraud Detection Backend

## Local setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the API

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI documentation.

## Run tests

```powershell
pytest
```