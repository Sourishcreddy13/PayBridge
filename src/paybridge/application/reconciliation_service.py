from datetime import date

from paybridge.domain.models import SettlementEntry
from paybridge.domain.reconciliation_rules import reconcile_entries

from .audit import AuditService
from .events import log_event
from .ports import PaymentRepository, RailReferenceLookup, SettlementRepository


class ReconciliationService:
    """Re-runnable: publishing an identical result for a line is a no-op, so repeated runs
    neither duplicate rows nor leave stale UNMATCHED results behind (latest result wins)."""

    def __init__(
        self,
        payments: PaymentRepository,
        settlements: SettlementRepository,
        audit: AuditService,
        references: RailReferenceLookup | None = None,
    ) -> None:
        self._payments = payments
        self._settlements = settlements
        self._audit = audit
        self._references = references

    def reconcile(self, business_date: date, actor: str, correlation_id: str) -> list[SettlementEntry]:
        entries = self._settlements.list_entries(business_date)
        payments = {p.payment_id: p for p in self._payments.list_settled(business_date)}
        references = (
            self._references.payment_ids_by_reference(e.external_reference for e in entries)
            if self._references is not None
            else {}
        )
        results = reconcile_entries(entries, payments, references)
        published = 0
        for result in results:
            if self._settlements.append_reconciliation_result(result):
                published += 1
                self._audit.record_event(
                    "RECONCILIATION_RESULT", actor, correlation_id, result.payment_id,
                    {"external_reference": result.external_reference, "status": result.status.value},
                )
        log_event(
            "reconciliation_run", correlation_id, actor=actor, business_date=business_date.isoformat(),
            lines=len(results), published=published,
        )
        return results
