from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Protocol


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


class Store(Protocol):
    def clear(self) -> None: ...

    def add_event(self, event: EventRecord) -> EventRecord: ...

    def has_event(self, event_id: str) -> bool: ...

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord: ...

    def get_decision(self, decision_id: str) -> DecisionRecord | None: ...

    def now(self) -> datetime: ...


class InMemoryStore:
    def __init__(self) -> None:
        self.events: dict[str, EventRecord] = {}
        self.decisions: dict[str, DecisionRecord] = {}

    def add_event(self, event: EventRecord) -> EventRecord:
        return self.events.setdefault(event.event_id, event)

    def clear(self) -> None:
        self.events.clear()
        self.decisions.clear()

    def has_event(self, event_id: str) -> bool:
        return event_id in self.events

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        self.decisions[decision.decision_id] = decision
        return decision

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self.decisions.get(decision_id)

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


class SQLiteStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                customer_id TEXT,
                application_id TEXT,
                correlation_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                combined_risk REAL NOT NULL,
                reason_codes TEXT NOT NULL,
                rule_version TEXT NOT NULL,
                feature_schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def add_event(self, event: EventRecord) -> EventRecord:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, event_type, customer_id, application_id,
                 correlation_id, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """ ,
            (
                event.event_id,
                event.event_type,
                event.customer_id,
                event.application_id,
                event.correlation_id,
                event.occurred_at.isoformat(),
            ),
        )
        self.connection.commit()
        return event

    def clear(self) -> None:
        self.connection.executescript("DELETE FROM events; DELETE FROM decisions;")
        self.connection.commit()

    def has_event(self, event_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO decisions
                (decision_id, correlation_id, decision, combined_risk,
                 reason_codes, rule_version, feature_schema_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.correlation_id,
                decision.decision,
                decision.combined_risk,
                json.dumps(decision.reason_codes),
                decision.rule_version,
                decision.feature_schema_version,
                decision.created_at.isoformat(),
            ),
        )
        self.connection.commit()
        return decision

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        row = self.connection.execute(
            "SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        if row is None:
            return None
        return DecisionRecord(
            decision_id=row["decision_id"],
            correlation_id=row["correlation_id"],
            decision=row["decision"],
            combined_risk=row["combined_risk"],
            reason_codes=tuple(json.loads(row["reason_codes"])),
            rule_version=row["rule_version"],
            feature_schema_version=row["feature_schema_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    def close(self) -> None:
        self.connection.close()


store = InMemoryStore()