from collections.abc import Sequence
from datetime import date
from uuid import UUID

from paybridge.domain.enums import PaymentState, ReconciliationStatus
from paybridge.domain.models import Payment, Refund, SettlementEntry
from .ports import PaymentRepository, RefundRepository, SettlementRepository, RoutingRepository


class OperationalQueueService:
    def __init__(self, payments: PaymentRepository, settlements: SettlementRepository, refunds: RefundRepository, routes: RoutingRepository) -> None:
        self._payments = payments
        self._settlements = settlements
        self._refunds = refunds
        self._routes = routes

    def unmatched(self, business_date: date) -> list[SettlementEntry]:
        return [entry for entry in self._settlements.list_reconciliation_results(business_date) if entry.status is ReconciliationStatus.UNMATCHED]

    def refunds(self) -> list[Refund]:
        return self._refunds.list_refunds()

    def retry_candidates(self, business_date: date) -> list[Payment]:
        candidates: list[Payment] = []
        for payment in self._payments.list_payments():
            if payment.created_at.date() != business_date:
                continue
            if self._payments.get_current_state(payment.payment_id) is PaymentState.PROCESSING:
                candidates.append(payment)
        return candidates

    def rail_breakdown(self, business_date: date) -> dict[str, int]:
        counts: dict[str, int] = {}
        for payment in self._payments.list_payments():
            if payment.created_at.date() != business_date:
                continue
            rail = self._routes.get_route(payment.payment_id)
            if rail is not None:
                counts[rail.value] = counts.get(rail.value, 0) + 1
        return counts

    def payment_state(self, payment_id: UUID) -> PaymentState:
        self._payments.get_payment(payment_id)
        return self._payments.get_current_state(payment_id)
