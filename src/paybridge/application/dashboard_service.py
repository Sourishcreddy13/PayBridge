from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from paybridge.domain.enums import PaymentState, Rail, ReconciliationStatus

from .dto import OpsSummaryView, QueuedPaymentView, RefundView, SettlementLineView
from .ports import RefundRepository, SettlementRepository


class OpsReadModel(Protocol):
    def payments_on(self, business_date: date) -> int: ...
    def volume_by_status(self, business_date: date) -> dict[str, int]: ...
    def volume_by_rail(self, business_date: date) -> dict[str, int]: ...
    def payments_in_state(
        self, business_date: date, state: PaymentState
    ) -> list[tuple[UUID, Rail | None, str, str]]: ...


class DashboardService:
    """Ops summary built from one aggregate read model instead of per-payment lookups."""

    def __init__(
        self, settlements: SettlementRepository, refunds: RefundRepository, read_model: OpsReadModel
    ) -> None:
        self._settlements = settlements
        self._refunds = refunds
        self._read_model = read_model

    def summary(self, business_date: date) -> OpsSummaryView:
        unmatched = [
            SettlementLineView(
                external_reference=e.external_reference,
                payment_id=e.payment_id,
                amount=e.amount,
                currency=e.currency,
                status=e.status,
            )
            for e in self._settlements.list_reconciliation_results(business_date)
            if e.status is ReconciliationStatus.UNMATCHED
        ]
        refund_views = [
            RefundView(
                refund_id=r.refund_id,
                original_payment_id=r.original_payment_id,
                reverse_payment_id=r.reverse_payment_id,
                amount=r.amount,
                status=r.status,
                requested_at=r.requested_at,
            )
            for r in self._refunds.list_refunds()
        ]
        def queue(state: PaymentState) -> list[QueuedPaymentView]:
            return [
                QueuedPaymentView(
                    payment_id=pid, rail=rail, amount=Decimal(amount), created_at=datetime.fromisoformat(created)
                )
                for pid, rail, amount, created in self._read_model.payments_in_state(business_date, state)
            ]

        return OpsSummaryView(
            business_date=business_date,
            payments_today=self._read_model.payments_on(business_date),
            volumes_by_rail=self._read_model.volume_by_rail(business_date),
            volumes_by_status=self._read_model.volume_by_status(business_date),
            unmatched_queue=unmatched,
            refund_queue=refund_views,
            pending_queue=queue(PaymentState.PENDING),
            retry_queue=queue(PaymentState.PROCESSING),
        )
