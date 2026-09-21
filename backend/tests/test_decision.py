from app.domain.decision import DecisionAction, FraudSignals, RiskEvidence, choose_action
from app.domain.rules import evaluate_rules


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