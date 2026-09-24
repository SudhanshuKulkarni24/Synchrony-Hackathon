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
        json={"correlation_id": "correlation-2", "feature_schema_version": "features-1.0.0"},
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


def test_review_decision_creates_case_and_feedback_closes_it() -> None:
    store.clear()
    response = client.post(
        "/api/v1/fraud/score",
        json={"correlation_id": "case-test", "is_new_device": True, "identity_match_score": 0.5},
    )
    cases = client.get("/api/v1/cases")
    case = cases.json()[0]
    updated = client.patch(
        f"/api/v1/cases/{case['case_id']}",
        json={"status": "CLOSED", "outcome": "CONFIRMED_FRAUD"},
    )

    assert response.json()["decision"] == "MANUAL_REVIEW"
    assert cases.status_code == 200
    assert case["decision_id"] == response.json()["decision_id"]
    assert updated.status_code == 200
    assert updated.json()["status"] == "CLOSED"
    assert updated.json()["outcome"] == "CONFIRMED_FRAUD"


def test_clean_decision_does_not_create_case() -> None:
    store.clear()

    response = client.post("/api/v1/fraud/score", json={"correlation_id": "clean-test"})

    assert response.json()["decision"] == "APPROVE"
    assert client.get("/api/v1/cases").json() == []


def test_metrics_track_decisions_and_cases() -> None:
    store.clear()
    client.post("/api/v1/fraud/score", json={"correlation_id": "metrics-clean"})
    client.post(
        "/api/v1/fraud/score",
        json={"correlation_id": "metrics-review", "is_new_device": True, "identity_match_score": 0.5},
    )

    metrics = client.get("/api/v1/metrics")

    assert metrics.status_code == 200
    assert metrics.json()["total_decisions"] == 2
    assert metrics.json()["approved"] == 1
    assert metrics.json()["manual_review"] == 1
    assert metrics.json()["open_cases"] == 1


def test_unsupported_feature_schema_is_rejected() -> None:
    response = client.post(
        "/api/v1/fraud/score",
        json={"feature_schema_version": "features-0.1.0"},
    )

    assert response.status_code == 422


def test_case_outcome_must_match_status() -> None:
    store.clear()
    score = client.post(
        "/api/v1/fraud/score",
        json={"is_new_device": True, "identity_match_score": 0.5},
    )
    case_id = client.get("/api/v1/cases").json()[0]["case_id"]

    response = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"status": "OPEN", "outcome": "LEGITIMATE"},
    )

    assert score.status_code == 200
    assert response.status_code == 422


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