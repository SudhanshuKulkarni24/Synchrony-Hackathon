from app.domain.decision import DecisionAction, FraudSignals, RiskEvidence, choose_action
from app.domain.rules import evaluate_rules
from app.main import app, store
from app.storage import SQLiteStore
from fastapi.testclient import TestClient


client = TestClient(app)


def test_clean_low_risk_transaction_is_approved() -> None:
    evidence = evaluate_rules(FraudSignals())

    assert choose_action(evidence, RiskEvidence()) == DecisionAction.APPROVE


def test_new_device_identity_mismatch_requires_review() -> None:
    evidence = evaluate_rules(
        FraudSignals(is_new_device=True, identity_match_score=0.5)
    )

    assert "NEW_DEVICE_IDENTITY_MISMATCH" in evidence.reason_codes
    assert choose_action(evidence, RiskEvidence()) == DecisionAction.MANUAL_REVIEW


def test_risky_network_is_hard_declined() -> None:
    evidence = evaluate_rules(FraudSignals(ip_risk_score=0.95))

    assert evidence.hard_decline is True
    assert choose_action(evidence, RiskEvidence()) == DecisionAction.DECLINE


def test_risk_score_is_clamped_and_combined() -> None:
    evidence = RiskEvidence(supervised_risk=1.0, anomaly_risk=1.0, graph_risk=1.0)

    assert evidence.combined_risk == 1.0
    assert choose_action(evaluate_rules(FraudSignals()), evidence) == DecisionAction.DECLINE


def test_event_ingestion_is_idempotent() -> None:
    store.clear()
    payload = {
        "event_id": "event-1",
        "event_type": "application_submitted",
        "correlation_id": "correlation-1",
        "application_id": "application-1",
        "occurred_at": "2026-09-21T12:00:00Z",
    }

    first = client.post("/api/v1/events", json=payload)
    second = client.post("/api/v1/events", json=payload)

    assert first.status_code == 202
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert store.has_event("event-1")


def test_score_can_be_retrieved_with_audit_metadata() -> None:
    store.clear()
    response = client.post(
        "/api/v1/fraud/score",
        json={"correlation_id": "correlation-2", "feature_schema_version": "features-1.0"},
    )
    decision = response.json()

    retrieved = client.get(f"/api/v1/decisions/{decision['decision_id']}")

    assert response.status_code == 200
    assert retrieved.status_code == 200
    assert retrieved.json() == decision
    assert decision["model_version"] in {"fraud-model-0.1.0", "fallback-0.1.0"}


def test_unknown_decision_returns_not_found() -> None:
    response = client.get("/api/v1/decisions/missing")

    assert response.status_code == 404


def test_sqlite_store_persists_decisions(tmp_path) -> None:
    sqlite_store = SQLiteStore(tmp_path / "fraud.db")
    response = client.post(
        "/api/v1/fraud/score",
        json={"correlation_id": "sqlite-test"},
    )
    decision_id = response.json()["decision_id"]
    record = store.get_decision(decision_id)

    assert record is not None
    sqlite_store.add_decision(record)
    sqlite_store.close()

    reopened = SQLiteStore(tmp_path / "fraud.db")
    persisted = reopened.get_decision(decision_id)

    assert persisted == record
    reopened.close()