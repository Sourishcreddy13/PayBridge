import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from paybridge.domain.enums import Rail, RailOutcome

from .db import Database


class SQLiteRailAttemptRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record_attempt(self, payment_id: UUID, rail: Rail, attempt: int, outcome: RailOutcome, external_reference: str | None, reason_code: str | None) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO rail_attempts(payment_id,rail,attempt,outcome,external_reference,reason_code,created_at) VALUES(?,?,?,?,?,?,?)", (str(payment_id), rail.value, attempt, outcome.value, external_reference, reason_code, datetime.now(UTC).isoformat()))
        except sqlite3.Error as exc:
            raise RuntimeError("Could not record rail attempt") from exc
        finally:
            conn.close()

    def list_attempts(self, payment_id: UUID) -> list[dict[str, str]]:
        conn = self._db.connection()
        try:
            rows = conn.execute("SELECT rail,attempt,outcome,external_reference,reason_code,created_at FROM rail_attempts WHERE payment_id=? ORDER BY id", (str(payment_id),)).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("Could not read rail attempts") from exc
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def payment_ids_by_reference(self, references: Iterable[str]) -> dict[str, UUID]:
        """Map rail external references (successful attempts) to the payment that produced them."""
        wanted = sorted(set(references))
        if not wanted:
            return {}
        conn = self._db.connection()
        try:
            marks = ",".join("?" for _ in wanted)
            rows = conn.execute(
                f"SELECT external_reference,payment_id FROM rail_attempts"
                f" WHERE outcome='SUCCESS' AND external_reference IN ({marks})",
                wanted,
            ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("Could not resolve settlement references") from exc
        finally:
            conn.close()
        return {row["external_reference"]: UUID(row["payment_id"]) for row in rows}
