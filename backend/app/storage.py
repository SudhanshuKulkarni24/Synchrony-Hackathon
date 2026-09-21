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
    model_version: str
    model_fallback: bool
    created_at: datetime


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    decision_id: str
    status: str
    outcome: str | None
    reason_codes: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class Store(Protocol):
    def clear(self) -> None: ...

    def add_event(self, event: EventRecord) -> EventRecord: ...

    def has_event(self, event_id: str) -> bool: ...

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord: ...

    def get_decision(self, decision_id: str) -> DecisionRecord | None: ...

    def add_case(self, case: CaseRecord) -> CaseRecord: ...

    def list_cases(self) -> list[CaseRecord]: ...

    def update_case(self, case_id: str, status: str, outcome: str) -> CaseRecord | None: ...

    def metrics(self) -> dict[str, int]: ...

    def now(self) -> datetime: ...


class InMemoryStore:
    def __init__(self) -> None:
        self.events: dict[str, EventRecord] = {}
        self.decisions: dict[str, DecisionRecord] = {}
        self.cases: dict[str, CaseRecord] = {}

    def add_event(self, event: EventRecord) -> EventRecord:
        return self.events.setdefault(event.event_id, event)

    def clear(self) -> None:
        self.events.clear()
        self.decisions.clear()
        self.cases.clear()

    def has_event(self, event_id: str) -> bool:
        return event_id in self.events

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        self.decisions[decision.decision_id] = decision
        return decision

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self.decisions.get(decision_id)

    def add_case(self, case: CaseRecord) -> CaseRecord:
        self.cases[case.case_id] = case
        return case

    def list_cases(self) -> list[CaseRecord]:
        return list(self.cases.values())

    def update_case(self, case_id: str, status: str, outcome: str) -> CaseRecord | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        updated = CaseRecord(
            case_id=case.case_id,
            decision_id=case.decision_id,
            status=status,
            outcome=outcome,
            reason_codes=case.reason_codes,
            created_at=case.created_at,
            updated_at=self.now(),
        )
        self.cases[case_id] = updated
        return updated

    def metrics(self) -> dict[str, int]:
        decisions = list(self.decisions.values())
        return {
            "total_decisions": len(decisions),
            "approved": sum(item.decision == "APPROVE" for item in decisions),
            "step_up": sum(item.decision == "STEP_UP" for item in decisions),
            "manual_review": sum(item.decision == "MANUAL_REVIEW" for item in decisions),
            "declined": sum(item.decision == "DECLINE" for item in decisions),
            "open_cases": sum(item.status == "OPEN" for item in self.cases.values()),
            "closed_cases": sum(item.status == "CLOSED" for item in self.cases.values()),
        }

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
                model_version TEXT NOT NULL DEFAULT 'stored-unknown',
                model_fallback INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fraud_cases (
                case_id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                reason_codes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(decisions)")
        }
        if "model_version" not in columns:
            self.connection.execute(
                "ALTER TABLE decisions ADD COLUMN model_version TEXT NOT NULL DEFAULT 'stored-unknown'"
            )
        if "model_fallback" not in columns:
            self.connection.execute(
                "ALTER TABLE decisions ADD COLUMN model_fallback INTEGER NOT NULL DEFAULT 0"
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
        self.connection.executescript(
            "DELETE FROM events; DELETE FROM decisions; DELETE FROM fraud_cases;"
        )
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
                  reason_codes, rule_version, feature_schema_version,
                  model_version, model_fallback, created_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.correlation_id,
                decision.decision,
                decision.combined_risk,
                json.dumps(decision.reason_codes),
                decision.rule_version,
                decision.feature_schema_version,
                decision.model_version,
                int(decision.model_fallback),
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
            model_version=row["model_version"],
            model_fallback=bool(row["model_fallback"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def add_case(self, case: CaseRecord) -> CaseRecord:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO fraud_cases
                (case_id, decision_id, status, outcome, reason_codes,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case.case_id,
                case.decision_id,
                case.status,
                case.outcome,
                json.dumps(case.reason_codes),
                case.created_at.isoformat(),
                case.updated_at.isoformat(),
            ),
        )
        self.connection.commit()
        return case

    def list_cases(self) -> list[CaseRecord]:
        rows = self.connection.execute(
            "SELECT * FROM fraud_cases ORDER BY created_at DESC"
        ).fetchall()
        return [self._case_from_row(row) for row in rows]

    def update_case(self, case_id: str, status: str, outcome: str) -> CaseRecord | None:
        existing = self.connection.execute(
            "SELECT * FROM fraud_cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        if existing is None:
            return None
        updated = CaseRecord(
            case_id=case_id,
            decision_id=existing["decision_id"],
            status=status,
            outcome=outcome,
            reason_codes=tuple(json.loads(existing["reason_codes"])),
            created_at=datetime.fromisoformat(existing["created_at"]),
            updated_at=self.now(),
        )
        return self.add_case(updated)

    def metrics(self) -> dict[str, int]:
        counts = self.connection.execute(
            """
            SELECT
                COUNT(*) AS total_decisions,
                SUM(decision = 'APPROVE') AS approved,
                SUM(decision = 'STEP_UP') AS step_up,
                SUM(decision = 'MANUAL_REVIEW') AS manual_review,
                SUM(decision = 'DECLINE') AS declined
            FROM decisions
            """
        ).fetchone()
        cases = self.connection.execute(
            """
            SELECT
                SUM(status = 'OPEN') AS open_cases,
                SUM(status = 'CLOSED') AS closed_cases
            FROM fraud_cases
            """
        ).fetchone()
        return {
            "total_decisions": counts["total_decisions"] or 0,
            "approved": counts["approved"] or 0,
            "step_up": counts["step_up"] or 0,
            "manual_review": counts["manual_review"] or 0,
            "declined": counts["declined"] or 0,
            "open_cases": cases["open_cases"] or 0,
            "closed_cases": cases["closed_cases"] or 0,
        }

    @staticmethod
    def _case_from_row(row: sqlite3.Row) -> CaseRecord:
        return CaseRecord(
            case_id=row["case_id"],
            decision_id=row["decision_id"],
            status=row["status"],
            outcome=row["outcome"],
            reason_codes=tuple(json.loads(row["reason_codes"])),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    def close(self) -> None:
        self.connection.close()


store = InMemoryStore()