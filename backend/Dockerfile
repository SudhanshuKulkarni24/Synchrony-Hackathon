FROM python:3.11-slim

WORKDIR /workspace
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY ml ml

ENV PYTHONPATH=/workspace
ENV FRAUD_STORE=sqlite
ENV FRAUD_DB_PATH=/data/fraud_detection.db

RUN python -m ml.training.train_models
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]