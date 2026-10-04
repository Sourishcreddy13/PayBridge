from datetime import date

from paybridge.domain.enums import ReconciliationStatus
from paybridge.domain.models import SettlementEntry
from paybridge.domain.reconciliation_rules import classify_entry

from .ports import PaymentRepository, SettlementRepository, AuditRepository


class ReconciliationService:
    def __init__(self, payments: PaymentRepository, settlements: SettlementRepository, audit: AuditRepository) -> None:
        self._payments = payments
        self._settlements = settlements
        self._audit = audit

    def reconcile(self, business_date: date, actor: str, correlation_id: str) -> list[SettlementEntry]:
        entries = self._settlements.list_entries(business_date)
        payments = {p.payment_id: p for p in self._payments.list_settled(business_date)}
        results: list[SettlementEntry] = []
        for entry in entries:
            payment = payments.get(entry.payment_id) if entry.payment_id else None
            status = ReconciliationStatus.MATCHED if payment and classify_entry(payment, entry) == "MATCHED" else ReconciliationStatus.UNMATCHED
            result = SettlementEntry(entry.external_reference, entry.payment_id, entry.amount, entry.currency, business_date, status)
            results.append(result)
            self._settlements.append_reconciliation_result(result)
            self._audit.record_event(
                "RECONCILIATION_RESULT", actor, correlation_id, entry.payment_id,
                {"external_reference": entry.external_reference, "status": status.value},
            )
        return results
