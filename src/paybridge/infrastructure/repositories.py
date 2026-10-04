import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus, RefundStatus
from paybridge.domain.exceptions import PaymentNotFound
from paybridge.domain.models import Beneficiary, Payment, PaymentTransition, Refund, RoutingDecision, SettlementEntry
from paybridge.domain.pii_policy import mask_account_number, mask_ifsc, mask_name

from .db import Database


class SQLitePaymentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def reserve_and_append_payment(self, payment: Payment) -> tuple[bool, UUID]:
        conn = self._db.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT payment_id FROM idempotency_keys WHERE idempotency_key=?", (payment.idempotency_key,)).fetchone()
            if existing is not None:
                conn.execute("ROLLBACK")
                return False, UUID(existing["payment_id"])
            conn.execute("INSERT INTO idempotency_keys(idempotency_key,payment_id,created_at) VALUES(?,?,?)", (payment.idempotency_key, str(payment.payment_id), payment.created_at.isoformat()))
            conn.execute(
                "INSERT INTO payments(payment_id,account_masked,ifsc_masked,beneficiary_name_masked,beneficiary_type,amount,currency,narration,idempotency_key,created_at,actor) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(payment.payment_id), mask_account_number(payment.beneficiary.account_number), mask_ifsc(payment.beneficiary.ifsc),
                    mask_name(payment.beneficiary.name), payment.beneficiary.beneficiary_type.value, str(payment.amount),
                    payment.currency, payment.narration, payment.idempotency_key, payment.created_at.isoformat(), payment.actor,
                ),
            )
            conn.execute("COMMIT")
            return True, payment.payment_id
        except sqlite3.Error as exc:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise RuntimeError("Could not atomically create payment") from exc
        finally:
            conn.close()

    def append_payment(self, payment: Payment) -> None:
        conn = self._db.connection()
        try:
            conn.execute(
                "INSERT INTO payments(payment_id,account_masked,ifsc_masked,beneficiary_name_masked,beneficiary_type,amount,currency,narration,idempotency_key,created_at,actor) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(payment.payment_id), mask_account_number(payment.beneficiary.account_number), mask_ifsc(payment.beneficiary.ifsc),
                    mask_name(payment.beneficiary.name), payment.beneficiary.beneficiary_type.value, str(payment.amount),
                    payment.currency, payment.narration, payment.idempotency_key, payment.created_at.isoformat(), payment.actor,
                ),
            )
        except sqlite3.Error as exc:
            raise RuntimeError("Could not append payment") from exc
        finally:
            conn.close()

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
        beneficiary = Beneficiary(
            account_number=f"00000000{row['account_masked'][-4:]}",
            ifsc=f"{row["ifsc_masked"][:4]}00000{row["ifsc_masked"][-2:]}",
            beneficiary_type=BeneficiaryType(row["beneficiary_type"]),
            name=row["beneficiary_name_masked"],
        )
        from datetime import datetime
        return Payment(UUID(row["payment_id"]), beneficiary, Decimal(row["amount"]), row["narration"], row["idempotency_key"], row["currency"], datetime.fromisoformat(row["created_at"]), row["actor"])

    def get_current_state(self, payment_id: UUID) -> PaymentState:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT to_state FROM payment_transitions WHERE payment_id=? ORDER BY id DESC LIMIT 1", (str(payment_id),)).fetchone()
        finally:
            conn.close()
        if row is None:
            return PaymentState.PENDING
        return PaymentState(row["to_state"])

    def append_transition(self, transition: PaymentTransition) -> None:
        conn = self._db.connection()
        try:
            conn.execute(
                "INSERT INTO payment_transitions(payment_id,from_state,to_state,at,actor,reason_code,reason) VALUES(?,?,?,?,?,?,?)",
                (str(transition.payment_id), transition.from_state.value, transition.to_state.value, transition.at.isoformat(), transition.actor, transition.reason_code, transition.reason),
            )
        except sqlite3.Error as exc:
            raise RuntimeError("Could not append payment transition") from exc
        finally:
            conn.close()

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
        return [self.get_payment(UUID(row["payment_id"])) for row in rows]

    def list_settled(self, business_date: date) -> list[Payment]:
        return [p for p in self.list_payments() if p.created_at.date() == business_date and self.get_current_state(p.payment_id) is PaymentState.SETTLED]

    def list_transitions(self, payment_id: UUID) -> list[PaymentTransition]:
        conn = self._db.connection()
        try:
            rows = conn.execute("SELECT * FROM payment_transitions WHERE payment_id=? ORDER BY id", (str(payment_id),)).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("Could not read payment timeline") from exc
        finally:
            conn.close()
        from datetime import datetime
        return [PaymentTransition(UUID(r["payment_id"]), PaymentState(r["from_state"]), PaymentState(r["to_state"]), datetime.fromisoformat(r["at"]), r["actor"], r["reason_code"], r["reason"]) for r in rows]



class SQLiteRoutingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_decision(self, decision: RoutingDecision) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO routing_decisions(payment_id,rail,reason,at,actor) VALUES(?,?,?,?,?)", (str(decision.payment_id), decision.rail.value, decision.reason, decision.at.isoformat(), decision.actor))
        finally:
            conn.close()

    def get_route(self, payment_id: UUID) -> Rail | None:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT rail FROM routing_decisions WHERE payment_id=? ORDER BY id DESC LIMIT 1", (str(payment_id),)).fetchone()
        finally:
            conn.close()
        return Rail(row["rail"]) if row else None


class SQLiteAuditRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_transition_audit(self, transition: PaymentTransition, correlation_id: str) -> None:
        payload = {"from_state": transition.from_state.value, "to_state": transition.to_state.value, "reason_code": transition.reason_code or ""}
        self.append_event("PAYMENT_TRANSITION", transition.actor, correlation_id, transition.payment_id, payload)

    def append_routing_audit(self, decision: RoutingDecision, correlation_id: str) -> None:
        self.append_event("ROUTING_DECISION", decision.actor, correlation_id, decision.payment_id, {"rail": decision.rail.value, "reason": decision.reason})

    def append_event(self, event_type: str, actor: str, correlation_id: str, payment_id: UUID | None, payload: dict[str, str]) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO audit_events(event_type,actor,correlation_id,payment_id,created_at,payload_json) VALUES(?,?,?,?,datetime('now'),?)", (event_type, actor, correlation_id, str(payment_id) if payment_id else None, json.dumps(payload, separators=(",", ":"))))
        finally:
            conn.close()


class SQLiteSettlementRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_entries(self, entries: list[SettlementEntry]) -> None:
        conn = self._db.connection()
        try:
            for entry in entries:
                conn.execute("INSERT INTO settlement_entries(external_reference,payment_id,amount,currency,business_date,status,created_at) VALUES(?,?,?,?,?,?,datetime('now'))", (entry.external_reference, str(entry.payment_id) if entry.payment_id else None, str(entry.amount), entry.currency, entry.business_date.isoformat(), entry.status.value))
        finally:
            conn.close()

    def list_entries(self, business_date: date) -> list[SettlementEntry]:
        conn = self._db.connection()
        try:
            rows = conn.execute("SELECT * FROM settlement_entries WHERE business_date=? ORDER BY id", (business_date.isoformat(),)).fetchall()
        finally:
            conn.close()
        return [SettlementEntry(row["external_reference"], UUID(row["payment_id"]) if row["payment_id"] else None, Decimal(row["amount"]), row["currency"], date.fromisoformat(row["business_date"]), ReconciliationStatus(row["status"])) for row in rows]

    def settlement_exists(self, business_date: date) -> bool:
        conn = self._db.connection()
        try:
            row = conn.execute("SELECT 1 FROM settlement_files WHERE business_date=?", (business_date.isoformat(),)).fetchone()
            return row is not None
        finally:
            conn.close()

    def append_file_record(self, business_date: date, path: str, checksum: str) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO settlement_files(business_date,path,checksum,created_at) VALUES(?,?,?,datetime('now'))", (business_date.isoformat(), path, checksum))
        finally:
            conn.close()

    def append_reconciliation_result(self, result: SettlementEntry) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO reconciliation_results(external_reference,payment_id,amount,currency,business_date,status,created_at) VALUES(?,?,?,?,?,?,datetime('now'))", (result.external_reference, str(result.payment_id) if result.payment_id else None, str(result.amount), result.currency, result.business_date.isoformat(), result.status.value))
        finally:
            conn.close()

    def list_reconciliation_results(self, business_date: date) -> list[SettlementEntry]:
        conn = self._db.connection()
        try:
            rows = conn.execute("SELECT * FROM reconciliation_results WHERE business_date=? ORDER BY id", (business_date.isoformat(),)).fetchall()
        finally:
            conn.close()
        return [SettlementEntry(row["external_reference"], UUID(row["payment_id"]) if row["payment_id"] else None, Decimal(row["amount"]), row["currency"], date.fromisoformat(row["business_date"]), ReconciliationStatus(row["status"])) for row in rows]


class SQLiteRefundRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append_refund(self, refund: Refund) -> None:
        conn = self._db.connection()
        try:
            conn.execute("INSERT INTO refunds(refund_id,original_payment_id,reverse_payment_id,amount,status,requested_at,actor) VALUES(?,?,?,?,?,?,?)", (str(refund.refund_id), str(refund.original_payment_id), str(refund.reverse_payment_id), str(refund.amount), refund.status.value, refund.requested_at.isoformat(), refund.actor))
        finally:
            conn.close()

    def list_refunds(self) -> list[Refund]:
        conn = self._db.connection()
        try:
            rows = conn.execute("SELECT * FROM refunds ORDER BY requested_at DESC").fetchall()
        finally:
            conn.close()
        from datetime import datetime
        return [Refund(UUID(r["refund_id"]), UUID(r["original_payment_id"]), UUID(r["reverse_payment_id"]), Decimal(r["amount"]), RefundStatus(r["status"]), datetime.fromisoformat(r["requested_at"]), r["actor"]) for r in rows]
