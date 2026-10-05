import json
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from paybridge.domain.enums import (
    BeneficiaryType,
    PaymentState,
    Rail,
    ReconciliationStatus,
    RefundStatus,
)
from paybridge.domain.exceptions import (
    InvalidPaymentStateException,
    PaymentNotFound,
    RefundNotAllowed,
    SettlementAlreadyExists,
    SettlementImportAlreadyExists,
    ValidationError,
)
from paybridge.domain.models import (
    Beneficiary,
    Payment,
    PaymentTransition,
    Refund,
    RoutingDecision,
    SettlementEntry,
)
from paybridge.domain.pii_policy import mask_account_number, mask_ifsc, mask_name
from paybridge.domain.settlement_policy import eligible_for_settlement
from paybridge.domain.state_machine import validate_transition

from .db import Database

# ---------------------------------------------------------------------------
# Statement helpers shared by repositories so multi-step writes use one transaction.
# ---------------------------------------------------------------------------


def _current_state(conn: sqlite3.Connection, payment_id: UUID) -> PaymentState:
    row = conn.execute(
        "SELECT to_state FROM payment_transitions WHERE payment_id=? ORDER BY id DESC LIMIT 1",
        (str(payment_id),),
    ).fetchone()
    return PaymentState(row["to_state"]) if row else PaymentState.PENDING


def _insert_audit(
    conn: sqlite3.Connection,
    event_type: str,
    actor: str,
    correlation_id: str,
    payment_id: UUID | None,
    payload: dict[str, str],
) -> None:
    conn.execute(
        "INSERT INTO audit_events(event_type,actor,correlation_id,payment_id,created_at,payload_json)"
        " VALUES(?,?,?,?,datetime('now'),?)",
        (
            event_type,
            actor,
            correlation_id,
            str(payment_id) if payment_id else None,
            json.dumps(payload, separators=(",", ":")),
        ),
    )


def _insert_transition(
    conn: sqlite3.Connection, transition: PaymentTransition, correlation_id: str | None
) -> None:
    """Append one lifecycle transition, enforcing legality against the *persisted* state.

    Must run inside a write transaction so the read and the insert are atomic.
    """
    current = _current_state(conn, transition.payment_id)
    if transition.from_state is not current:
        raise InvalidPaymentStateException(current.value, transition.to_state.value)
    validate_transition(current, transition.to_state)
    conn.execute(
        "INSERT INTO payment_transitions(payment_id,from_state,to_state,at,actor,reason_code,reason)"
        " VALUES(?,?,?,?,?,?,?)",
        (
            str(transition.payment_id),
            transition.from_state.value,
            transition.to_state.value,
            transition.at.isoformat(),
            transition.actor,
            transition.reason_code,
            transition.reason,
        ),
    )
    if correlation_id is not None:
        _insert_audit(
            conn,
            "PAYMENT_TRANSITION",
            transition.actor,
            correlation_id,
            transition.payment_id,
            {
                "from_state": transition.from_state.value,
                "to_state": transition.to_state.value,
                "reason_code": transition.reason_code or "",
            },
        )


def _insert_routing(
    conn: sqlite3.Connection, decision: RoutingDecision, correlation_id: str | None
) -> None:
    conn.execute(
        "INSERT INTO routing_decisions(payment_id,rail,reason,at,actor) VALUES(?,?,?,?,?)",
        (str(decision.payment_id), decision.rail.value, decision.reason, decision.at.isoformat(), decision.actor),
    )
    if correlation_id is not None:
        _insert_audit(
            conn,
            "ROUTING_DECISION",
            decision.actor,
            correlation_id,
            decision.payment_id,
            {"rail": decision.rail.value, "reason": decision.reason},
        )


def _insert_payment(conn: sqlite3.Connection, payment: Payment) -> None:
    conn.execute(
        "INSERT INTO payments(payment_id,account_masked,ifsc_masked,beneficiary_name_masked,"
        "beneficiary_type,amount,currency,narration,idempotency_key,created_at,actor)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            str(payment.payment_id),
            mask_account_number(payment.beneficiary.account_number),
            mask_ifsc(payment.beneficiary.ifsc),
            mask_name(payment.beneficiary.name),
            payment.beneficiary.beneficiary_type.value,
            str(payment.amount),
            payment.currency,
            payment.narration,
            payment.idempotency_key,
            payment.created_at.isoformat(),
            payment.actor,
        ),
    )


class SQLitePaymentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def reserve_and_append_payment(
        self,
        payment: Payment,
        decision: RoutingDecision | None = None,
        correlation_id: str | None = None,
    ) -> tuple[bool, UUID]:
        """Atomically reserve the idempotency key and persist payment, routing and audit.

        Returns ``(False, original_id)`` for a replay. Nothing is persisted unless every
        part (payment, routing decision, audit events) is.
        """
        try:
            with self._db.transaction() as conn:
                existing = conn.execute(
                    "SELECT payment_id FROM idempotency_keys WHERE idempotency_key=?",
                    (payment.idempotency_key,),
                ).fetchone()
                if existing is not None:
                    return False, UUID(existing["payment_id"])
                conn.execute(
                    "INSERT INTO idempotency_keys(idempotency_key,payment_id,created_at) VALUES(?,?,?)",
                    (payment.idempotency_key, str(payment.payment_id), payment.created_at.isoformat()),
                )
                _insert_payment(conn, payment)
                if correlation_id is not None:
                    _insert_audit(
                        conn, "PAYMENT_CREATED", payment.actor, correlation_id, payment.payment_id,
                        {"initial_state": PaymentState.PENDING.value},
                    )
                if decision is not None:
                    _insert_routing(conn, decision, correlation_id)
                return True, payment.payment_id
        except sqlite3.Error as exc:
            raise RuntimeError("Could not atomically create payment") from exc

    def get_payment(self, payment_id: UUID) -> Payment:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT * FROM payments WHERE payment_id=?", (str(payment_id),)).fetchone()
        except sqlite3.Error as exc:
            raise RuntimeError("Could not read payment") from exc
        finally:
            conn.close()
        if row is None:
            raise PaymentNotFound(str(payment_id))
        return _row_to_payment(row)

    def get_current_state(self, payment_id: UUID) -> PaymentState:
        conn = self._db.connection()
        try:
            return _current_state(conn, payment_id)
        finally:
            conn.close()

    def append_transition(self, transition: PaymentTransition, correlation_id: str | None = None) -> None:
        """Atomically append a legal transition from the persisted current state.

        Raises InvalidPaymentStateException when ``from_state`` is stale, which is how a
        concurrent second caller loses before it can reach a payment rail.
        """
        try:
            with self._db.transaction() as conn:
                _insert_transition(conn, transition, correlation_id)
        except sqlite3.Error as exc:
            raise RuntimeError("Could not append payment transition") from exc

    def latest_transition(self, payment_id: UUID) -> PaymentTransition | None:
        transitions = self.list_transitions(payment_id)
        return transitions[-1] if transitions else None

    def count_payments_for_key(self, key: str) -> int:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM payments WHERE idempotency_key=?", (key,)).fetchone()
            return int(row["n"])
        finally:
            conn.close()

    def list_payments(self, actor: str | None = None) -> list[Payment]:
        conn = self._db.connection()
        try:
            if actor:
                rows = conn.execute("SELECT * FROM payments WHERE actor=? ORDER BY created_at DESC", (actor,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM payments ORDER BY created_at DESC").fetchall()
        finally:
            conn.close()
        return [_row_to_payment(row) for row in rows]

    def list_settled(self, business_date: date) -> list[Payment]:
        """Payments that have a SETTLED transition on ``business_date`` (even if refunded since)."""
        conn = self._db.connection()
        try:
            ids = [
                row["payment_id"]
                for row in conn.execute(
                    "SELECT DISTINCT payment_id FROM payment_transitions WHERE to_state='SETTLED'"
                    " AND date(at) BETWEEN date(?, '-1 day') AND date(?, '+1 day')",
                    (business_date.isoformat(), business_date.isoformat()),
                )
            ]
        finally:
            conn.close()
        settled: list[Payment] = []
        for payment_id in ids:
            if eligible_for_settlement(self.list_transitions(UUID(payment_id)), business_date):
                settled.append(self.get_payment(UUID(payment_id)))
        return settled

    def list_transitions(self, payment_id: UUID) -> list[PaymentTransition]:
        conn = self._db.connection()
        try:
            rows = conn.execute(
                "SELECT * FROM payment_transitions WHERE payment_id=? ORDER BY id", (str(payment_id),)
            ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("Could not read payment timeline") from exc
        finally:
            conn.close()
        return [
            PaymentTransition(
                UUID(r["payment_id"]), PaymentState(r["from_state"]), PaymentState(r["to_state"]),
                datetime.fromisoformat(r["at"]), r["actor"], r["reason_code"], r["reason"],
            )
            for r in rows
        ]


def _row_to_payment(row: sqlite3.Row) -> Payment:
    beneficiary = Beneficiary(
        account_number=f"00000000{row['account_masked'][-4:]}",
        ifsc=f"{row['ifsc_masked'][:4]}00000{row['ifsc_masked'][-2:]}",
        beneficiary_type=BeneficiaryType(row["beneficiary_type"]),
        name=row["beneficiary_name_masked"],
    )
    return Payment(
        UUID(row["payment_id"]), beneficiary, Decimal(row["amount"]), row["narration"],
        row["idempotency_key"], row["currency"], datetime.fromisoformat(row["created_at"]), row["actor"],
    )


class SQLiteRoutingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_decision(self, decision: RoutingDecision) -> None:
        with self._db.transaction() as conn:
            _insert_routing(conn, decision, None)

    def get_route(self, payment_id: UUID) -> Rail | None:
        conn = self._db.connection()
        try:
            row = conn.execute(
                "SELECT rail FROM routing_decisions WHERE payment_id=? ORDER BY id DESC LIMIT 1",
                (str(payment_id),),
            ).fetchone()
        finally:
            conn.close()
        return Rail(row["rail"]) if row else None


class SQLiteAuditRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_transition_audit(self, transition: PaymentTransition, correlation_id: str) -> None:
        payload = {
            "from_state": transition.from_state.value,
            "to_state": transition.to_state.value,
            "reason_code": transition.reason_code or "",
        }
        self.append_event("PAYMENT_TRANSITION", transition.actor, correlation_id, transition.payment_id, payload)

    def append_routing_audit(self, decision: RoutingDecision, correlation_id: str) -> None:
        self.append_event(
            "ROUTING_DECISION", decision.actor, correlation_id, decision.payment_id,
            {"rail": decision.rail.value, "reason": decision.reason},
        )

    def append_event(
        self, event_type: str, actor: str, correlation_id: str, payment_id: UUID | None, payload: dict[str, str]
    ) -> None:
        with self._db.transaction() as conn:
            _insert_audit(conn, event_type, actor, correlation_id, payment_id, payload)


def _row_to_entry(row: sqlite3.Row) -> SettlementEntry:
    return SettlementEntry(
        row["external_reference"],
        UUID(row["payment_id"]) if row["payment_id"] else None,
        Decimal(row["amount"]),
        row["currency"],
        date.fromisoformat(row["business_date"]),
        ReconciliationStatus(row["status"]),
    )


def _insert_entries(conn: sqlite3.Connection, entries: Iterable[SettlementEntry]) -> None:
    for entry in entries:
        conn.execute(
            "INSERT INTO settlement_entries(external_reference,payment_id,amount,currency,business_date,status,created_at)"
            " VALUES(?,?,?,?,?,?,datetime('now'))",
            (
                entry.external_reference,
                str(entry.payment_id) if entry.payment_id else None,
                str(entry.amount),
                entry.currency,
                entry.business_date.isoformat(),
                entry.status.value,
            ),
        )


class SQLiteSettlementRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_entries(self, entries: list[SettlementEntry]) -> None:
        try:
            with self._db.transaction() as conn:
                _insert_entries(conn, entries)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Duplicate settlement external reference for business date") from exc

    def import_entries(
        self, entries: list[SettlementEntry], checksum: str, business_date: date, actor: str
    ) -> None:
        """Atomically record an import identity and its entries; identical re-imports are rejected."""
        try:
            with self._db.transaction() as conn:
                if conn.execute(
                    "SELECT 1 FROM settlement_imports WHERE checksum=?", (checksum,)
                ).fetchone():
                    raise SettlementImportAlreadyExists("This settlement file was already imported")
                conn.execute(
                    "INSERT INTO settlement_imports(checksum,business_date,entry_count,actor,created_at)"
                    " VALUES(?,?,?,?,datetime('now'))",
                    (checksum, business_date.isoformat(), len(entries), actor),
                )
                _insert_entries(conn, entries)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Duplicate settlement external reference for business date") from exc

    def list_entries(self, business_date: date) -> list[SettlementEntry]:
        conn = self._db.connection()
        try:
            rows = conn.execute(
                "SELECT * FROM settlement_entries WHERE business_date=? ORDER BY id", (business_date.isoformat(),)
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_entry(row) for row in rows]

    def settlement_exists(self, business_date: date) -> bool:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT 1 FROM settlement_files WHERE business_date=?", (business_date.isoformat(),)).fetchone()
            return row is not None
        finally:
            conn.close()

    def append_file_record(self, business_date: date, path: str, checksum: str) -> None:
        try:
            with self._db.transaction() as conn:
                conn.execute(
                    "INSERT INTO settlement_files(business_date,path,checksum,created_at) VALUES(?,?,?,datetime('now'))",
                    (business_date.isoformat(), path, checksum),
                )
        except sqlite3.IntegrityError as exc:
            raise SettlementAlreadyExists(f"Settlement already exists for {business_date.isoformat()}") from exc

    def append_reconciliation_result(self, result: SettlementEntry) -> bool:
        """Publish a result unless the latest result for the same line is identical (idempotent).

        Returns True when a new row was appended.
        """
        with self._db.transaction() as conn:
            latest = conn.execute(
                "SELECT payment_id,amount,currency,status FROM reconciliation_results"
                " WHERE business_date=? AND external_reference=? ORDER BY id DESC LIMIT 1",
                (result.business_date.isoformat(), result.external_reference),
            ).fetchone()
            candidate = (
                str(result.payment_id) if result.payment_id else None,
                str(result.amount),
                result.currency,
                result.status.value,
            )
            if latest is not None and tuple(latest) == candidate:
                return False
            conn.execute(
                "INSERT INTO reconciliation_results(external_reference,payment_id,amount,currency,business_date,status,created_at)"
                " VALUES(?,?,?,?,?,?,datetime('now'))",
                (
                    result.external_reference,
                    str(result.payment_id) if result.payment_id else None,
                    str(result.amount),
                    result.currency,
                    result.business_date.isoformat(),
                    result.status.value,
                ),
            )
            return True

    def list_reconciliation_results(self, business_date: date) -> list[SettlementEntry]:
        """Latest published result per settlement line (history stays in the append-only table)."""
        conn = self._db.connection()
        try:
            rows = conn.execute(
                "SELECT * FROM reconciliation_results WHERE id IN ("
                " SELECT MAX(id) FROM reconciliation_results WHERE business_date=? GROUP BY external_reference)"
                " ORDER BY id",
                (business_date.isoformat(),),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_entry(row) for row in rows]


_REFUND_SELECT = (
    "SELECT r.refund_id,r.original_payment_id,r.reverse_payment_id,r.amount,r.requested_at,r.actor,"
    "COALESCE(x.status,'PENDING') AS status FROM refunds r"
    " LEFT JOIN refund_resolutions x ON x.refund_id = r.refund_id"
)


def _row_to_refund(r: sqlite3.Row) -> Refund:
    return Refund(
        UUID(r["refund_id"]), UUID(r["original_payment_id"]), UUID(r["reverse_payment_id"]),
        Decimal(r["amount"]), RefundStatus(r["status"]), datetime.fromisoformat(r["requested_at"]), r["actor"],
    )


class SQLiteRefundRepository:
    """Refunds are append-only: a request row, then at most one immutable resolution row."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append_refund(self, refund: Refund, correlation_id: str | None = None) -> None:
        """Persist a refund request. Only one refund request may ever exist per payment."""
        try:
            with self._db.transaction() as conn:
                conn.execute(
                    "INSERT INTO refunds(refund_id,original_payment_id,reverse_payment_id,amount,status,requested_at,actor)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (
                        str(refund.refund_id), str(refund.original_payment_id), str(refund.reverse_payment_id),
                        str(refund.amount), RefundStatus.PENDING.value, refund.requested_at.isoformat(), refund.actor,
                    ),
                )
                if correlation_id is not None:
                    _insert_audit(
                        conn, "REFUND_REQUESTED", refund.actor, correlation_id, refund.original_payment_id,
                        {"refund_id": str(refund.refund_id)},
                    )
        except sqlite3.IntegrityError as exc:
            raise RefundNotAllowed("A refund has already been requested for this payment") from exc

    def get_refund(self, refund_id: UUID) -> Refund | None:
        conn = self._db.connection()
        try:
            row = conn.execute(_REFUND_SELECT + " WHERE r.refund_id=?", (str(refund_id),)).fetchone()
        finally:
            conn.close()
        return _row_to_refund(row) if row else None

    def get_refund_for_payment(self, payment_id: UUID) -> Refund | None:
        conn = self._db.connection()
        try:
            row = conn.execute(_REFUND_SELECT + " WHERE r.original_payment_id=?", (str(payment_id),)).fetchone()
        finally:
            conn.close()
        return _row_to_refund(row) if row else None

    def complete_refund(
        self, refund: Refund, transition: PaymentTransition, currency: str, correlation_id: str
    ) -> None:
        """Atomically: SETTLED->REFUNDED, reverse-payment ledger entry, resolution, audit."""
        try:
            with self._db.transaction() as conn:
                if self._resolved(conn, refund.refund_id):
                    raise RefundNotAllowed("Refund has already been resolved")
                _insert_transition(conn, transition, correlation_id)
                conn.execute(
                    "INSERT INTO reverse_payments(reverse_payment_id,original_payment_id,amount,currency,created_at,actor)"
                    " VALUES(?,?,?,?,?,?)",
                    (
                        str(refund.reverse_payment_id), str(refund.original_payment_id), str(refund.amount),
                        currency, transition.at.isoformat(), transition.actor,
                    ),
                )
                conn.execute(
                    "INSERT INTO refund_resolutions(refund_id,status,reason,resolved_at,actor) VALUES(?,?,?,?,?)",
                    (str(refund.refund_id), RefundStatus.COMPLETED.value, None, transition.at.isoformat(), transition.actor),
                )
                _insert_audit(
                    conn, "REFUND_COMPLETED", transition.actor, correlation_id, refund.original_payment_id,
                    {"refund_id": str(refund.refund_id), "reverse_payment_id": str(refund.reverse_payment_id)},
                )
        except sqlite3.IntegrityError as exc:
            raise RefundNotAllowed("Refund could not be completed") from exc

    def fail_refund(self, refund: Refund, reason: str, actor: str, correlation_id: str, at: datetime) -> None:
        try:
            with self._db.transaction() as conn:
                if self._resolved(conn, refund.refund_id):
                    raise RefundNotAllowed("Refund has already been resolved")
                conn.execute(
                    "INSERT INTO refund_resolutions(refund_id,status,reason,resolved_at,actor) VALUES(?,?,?,?,?)",
                    (str(refund.refund_id), RefundStatus.FAILED.value, reason, at.isoformat(), actor),
                )
                _insert_audit(
                    conn, "REFUND_REJECTED", actor, correlation_id, refund.original_payment_id,
                    {"refund_id": str(refund.refund_id), "reason": reason},
                )
        except sqlite3.IntegrityError as exc:
            raise RefundNotAllowed("Refund could not be rejected") from exc

    @staticmethod
    def _resolved(conn: sqlite3.Connection, refund_id: UUID) -> bool:
        return conn.execute(
            "SELECT 1 FROM refund_resolutions WHERE refund_id=?", (str(refund_id),)
        ).fetchone() is not None

    def list_refunds(self) -> list[Refund]:
        conn = self._db.connection()
        try:
            rows = conn.execute(_REFUND_SELECT + " ORDER BY r.requested_at DESC").fetchall()
        finally:
            conn.close()
        return [_row_to_refund(r) for r in rows]
