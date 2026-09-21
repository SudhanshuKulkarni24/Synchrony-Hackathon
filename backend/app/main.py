from datetime import datetime
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .domain.decision import FraudSignals, RiskEvidence, choose_action
from .domain.rules import evaluate_rules
from .features.builder import FEATURE_SCHEMA_VERSION, build_features
from .model_service import FraudModel
from .storage import DecisionRecord, EventRecord, InMemoryStore, SQLiteStore, Store


app = FastAPI(
    title="Real-Time Fraud Detection API",
    version="0.1.0",
    description="Deterministic fraud decision foundation for the lending prototype.",
)


def create_store() -> Store:
    if os.getenv("FRAUD_STORE", "memory").lower() == "sqlite":
        return SQLiteStore(os.getenv("FRAUD_DB_PATH", "fraud_detection.db"))
    return InMemoryStore()


store = create_store()
fraud_model = FraudModel()


class ScoreRequest(BaseModel):
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    
    applications_last_24h: int = Field(default=0, ge=0)
    is_new_device: bool = False
    identity_match_score: float = Field(default=1.0, ge=0.0, le=1.0)
    device_account_count: int = Field(default=1, ge=1)
    payment_account_count: int = Field(default=1, ge=1)
    ip_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    supervised_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    anomaly_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    graph_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class ScoreResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    decision_id: str
    correlation_id: str
    decision: str
    combined_risk: float
    reason_codes: list[str]
    rule_version: str
    feature_schema_version: str
    model_version: str
    model_fallback: bool


class EventRequest(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    customer_id: str | None = None
    application_id: str | None = None
    occurred_at: datetime


class EventResponse(BaseModel):
    event_id: str
    accepted: bool
    duplicate: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/events", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(request: EventRequest) -> EventResponse:
    event = EventRecord(
        event_id=request.event_id,
        event_type=request.event_type,
        customer_id=request.customer_id,
        application_id=request.application_id,
        correlation_id=request.correlation_id,
        occurred_at=request.occurred_at,
    )
    duplicate = store.has_event(request.event_id)
    store.add_event(event)
    return EventResponse(
        event_id=request.event_id,
        accepted=True,
        duplicate=duplicate,
    )


@app.post("/api/v1/fraud/score", response_model=ScoreResponse)
def score_fraud(request: ScoreRequest) -> ScoreResponse:
    feature_vector = build_features(request.model_dump())
    features = feature_vector.as_dict()
    signals = FraudSignals(
        applications_last_24h=int(features["applications_last_24h"]),
        is_new_device=bool(features["is_new_device"]),
        identity_match_score=features["identity_match_score"],
        device_account_count=int(features["device_account_count"]),
        payment_account_count=int(features["payment_account_count"]),
        ip_risk_score=features["ip_risk_score"],
    )
    rule_evidence = evaluate_rules(signals)
    model_evidence = fraud_model.predict(feature_vector)
    risk_evidence = RiskEvidence(
        supervised_risk=(
            request.supervised_risk
            if request.supervised_risk > 0
            else model_evidence.supervised_risk
        ),
        anomaly_risk=(
            request.anomaly_risk
            if request.anomaly_risk > 0
            else model_evidence.anomaly_risk
        ),
        graph_risk=request.graph_risk,
    )
    decision = choose_action(rule_evidence, risk_evidence)
    decision_record = DecisionRecord(
        decision_id=str(uuid4()),
        correlation_id=request.correlation_id,
        decision=decision,
        combined_risk=round(risk_evidence.combined_risk, 4),
        reason_codes=rule_evidence.reason_codes,
        rule_version="rules-0.1.0",
        feature_schema_version=request.feature_schema_version,
        model_version=model_evidence.model_version,
        model_fallback=model_evidence.used_fallback,
        created_at=store.now(),
    )
    store.add_decision(decision_record)
    return ScoreResponse(
        decision_id=decision_record.decision_id,
        correlation_id=decision_record.correlation_id,
        decision=decision_record.decision,
        combined_risk=round(risk_evidence.combined_risk, 4),
        reason_codes=list(rule_evidence.reason_codes),
        rule_version="rules-0.1.0",
        feature_schema_version=request.feature_schema_version,
        model_version=decision_record.model_version,
        model_fallback=decision_record.model_fallback,
    )


@app.get("/api/v1/decisions/{decision_id}", response_model=ScoreResponse)
def get_decision(decision_id: str) -> ScoreResponse:
    record = store.get_decision(decision_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return ScoreResponse(
        decision_id=record.decision_id,
        correlation_id=record.correlation_id,
        decision=record.decision,
        combined_risk=record.combined_risk,
        reason_codes=list(record.reason_codes),
        rule_version=record.rule_version,
        feature_schema_version=record.feature_schema_version,
        model_version=record.model_version,
        model_fallback=record.model_fallback,
    )