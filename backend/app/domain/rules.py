from .decision import FraudSignals, RuleEvidence


def evaluate_rules(signals: FraudSignals) -> RuleEvidence:
    reasons: list[str] = []
    hard_decline = False

    if signals.applications_last_24h >= 5:
        reasons.append("HIGH_APPLICATION_VELOCITY")

    if signals.is_new_device and signals.identity_match_score < 0.80:
        reasons.append("NEW_DEVICE_IDENTITY_MISMATCH")

    if signals.device_account_count >= 4:
        reasons.append("SHARED_DEVICE")

    if signals.payment_account_count >= 4:
        reasons.append("SHARED_PAYMENT_INSTRUMENT")

    if signals.ip_risk_score >= 0.90:
        reasons.append("KNOWN_RISKY_NETWORK")
        hard_decline = True

    return RuleEvidence(reason_codes=tuple(reasons), hard_decline=hard_decline)