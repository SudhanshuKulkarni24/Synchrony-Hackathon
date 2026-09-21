from fastapi import FastAPI
from pydantic import BaseModel, Field

from .domain.decision import FraudSignals, RiskEvidence, choose_action
from .domain.rules import evaluate_rules


app = FastAPI(
    title="Real-Time Fraud Detection API",
    version="0.1.0",
    description="Deterministic fraud decision foundation for the lending prototype.",
)


class ScoreRequest(BaseModel):
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
    decision: str
    combined_risk: float
    reason_codes: list[str]
    rule_version: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/fraud/score", response_model=ScoreResponse)
def score_fraud(request: ScoreRequest) -> ScoreResponse:
    signals = FraudSignals(
        applications_last_24h=request.applications_last_24h,
        is_new_device=request.is_new_device,
        identity_match_score=request.identity_match_score,
        device_account_count=request.device_account_count,
        payment_account_count=request.payment_account_count,
        ip_risk_score=request.ip_risk_score,
    )
    rule_evidence = evaluate_rules(signals)
    risk_evidence = RiskEvidence(
        supervised_risk=request.supervised_risk,
        anomaly_risk=request.anomaly_risk,
        graph_risk=request.graph_risk,
    )
    return ScoreResponse(
        decision=choose_action(rule_evidence, risk_evidence),
        combined_risk=round(risk_evidence.combined_risk, 4),
        reason_codes=list(rule_evidence.reason_codes),
        rule_version="rules-0.1.0",
    )