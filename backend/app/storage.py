from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    event_type: str
    customer_id: str | None
    application_id: str | None
    correlation_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    correlation_id: str
    decision: str
    combined_risk: float
    reason_codes: tuple[str, ...]
    rule_version: str
    feature_schema_version: str
    created_at: datetime


class InMemoryStore:
    def __init__(self) -> None:
        self.events: dict[str, EventRecord] = {}
        self.decisions: dict[str, DecisionRecord] = {}

    def add_event(self, event: EventRecord) -> EventRecord:
        return self.events.setdefault(event.event_id, event)

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        self.decisions[decision.decision_id] = decision
        return decision

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self.decisions.get(decision_id)

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


store = InMemoryStore()