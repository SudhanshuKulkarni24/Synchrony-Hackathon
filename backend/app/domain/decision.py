from dataclasses import dataclass
from enum import StrEnum


class DecisionAction(StrEnum):
    APPROVE = "APPROVE"
    STEP_UP = "STEP_UP"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    DECLINE = "DECLINE"


@dataclass(frozen=True)
class FraudSignals:
    applications_last_24h: int = 0
    is_new_device: bool = False
    identity_match_score: float = 1.0
    device_account_count: int = 1
    payment_account_count: int = 1
    ip_risk_score: float = 0.0


@dataclass(frozen=True)
class RuleEvidence:
    reason_codes: tuple[str, ...]
    hard_decline: bool = False


@dataclass(frozen=True)
class RiskEvidence:
    supervised_risk: float = 0.0
    anomaly_risk: float = 0.0
    graph_risk: float = 0.0

    @property
    def combined_risk(self) -> float:
        value = (
            0.60 * self.supervised_risk
            + 0.20 * self.anomaly_risk
            + 0.20 * self.graph_risk
        )
        return max(0.0, min(1.0, value))


def choose_action(evidence: RuleEvidence, risk: RiskEvidence) -> DecisionAction:
    if evidence.hard_decline or risk.combined_risk >= 0.85:
        return DecisionAction.DECLINE
    if risk.combined_risk >= 0.65 or evidence.reason_codes:
        return DecisionAction.MANUAL_REVIEW
    if risk.combined_risk >= 0.35:
        return DecisionAction.STEP_UP
    return DecisionAction.APPROVE