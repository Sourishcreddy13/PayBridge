from collections import Counter
from datetime import date

from paybridge.domain.enums import PaymentState, ReconciliationStatus
from .dto import OpsSummaryView, RefundView, SettlementLineView
from .ports import PaymentRepository, RefundRepository, RoutingRepository, SettlementRepository


class DashboardService:
    def __init__(self, payments: PaymentRepository, routes: RoutingRepository, settlements: SettlementRepository, refunds: RefundRepository, read_model=None) -> None:
        self._payments = payments
        self._routes = routes
        self._settlements = settlements
        self._refunds = refunds
        self._read_model = read_model

    def summary(self, business_date: date) -> OpsSummaryView:
        payments = [p for p in self._payments.list_payments() if p.created_at.date() == business_date]
        by_rail = Counter()
        by_status = Counter()
        for payment in payments:
            state = self._payments.get_current_state(payment.payment_id)
            by_status[state.value] += 1
            route = self._routes.get_route(payment.payment_id)
            if route:
                by_rail[route.value] += 1
        unmatched = [
            SettlementLineView(external_reference=e.external_reference, payment_id=e.payment_id, amount=e.amount, currency=e.currency, status=e.status)
            for e in self._settlements.list_reconciliation_results(business_date)
            if e.status is ReconciliationStatus.UNMATCHED
        ]
        refund_views = [
            RefundView(refund_id=r.refund_id, original_payment_id=r.original_payment_id, reverse_payment_id=r.reverse_payment_id, amount=r.amount, status=r.status, requested_at=r.requested_at)
            for r in self._refunds.list_refunds()
        ]
        return OpsSummaryView(volumes_by_rail=dict(by_rail), volumes_by_status=dict(by_status), unmatched_queue=unmatched, refund_queue=refund_views)
