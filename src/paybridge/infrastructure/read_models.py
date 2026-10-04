from collections import Counter
from datetime import date
from uuid import UUID

from paybridge.domain.enums import PaymentState
from .db import Database


class SQLiteOpsReadModel:
    def __init__(self, db: Database) -> None:
        self._db = db

    def volume_by_status(self, business_date: date) -> dict[str, int]:
        conn = self._db.connection()
        try:
            rows = conn.execute("""
                SELECT pt.to_state, COUNT(*) AS n
                FROM payments p
                LEFT JOIN payment_transitions pt ON pt.id = (
                    SELECT id FROM payment_transitions x WHERE x.payment_id = p.payment_id ORDER BY id DESC LIMIT 1
                )
                WHERE date(p.created_at) = ?
                GROUP BY pt.to_state
            """, (business_date.isoformat(),)).fetchall()
        finally:
            conn.close()
        result = {state.value: 0 for state in PaymentState}
        for row in rows:
            result[row["to_state"] or PaymentState.PENDING.value] = int(row["n"])
        return result

    def volume_by_rail(self, business_date: date) -> dict[str, int]:
        conn = self._db.connection()
        try:
            rows = conn.execute("""
                SELECT r.rail, COUNT(*) AS n
                FROM payments p
                JOIN routing_decisions r ON r.id = (
                    SELECT id FROM routing_decisions x WHERE x.payment_id = p.payment_id ORDER BY id DESC LIMIT 1
                )
                WHERE date(p.created_at) = ?
                GROUP BY r.rail
            """, (business_date.isoformat(),)).fetchall()
        finally:
            conn.close()
        return {row["rail"]: int(row["n"]) for row in rows}

    def unmatched_count(self, business_date: date) -> int:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM reconciliation_results WHERE business_date=? AND status='UNMATCHED'", (business_date.isoformat(),)).fetchone()
            return int(row["n"]) if row else 0
        finally:
            conn.close()
