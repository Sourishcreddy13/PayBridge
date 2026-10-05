from decimal import Decimal
from uuid import UUID, uuid4

from paybridge.domain.enums import PaymentState, RefundStatus
from paybridge.domain.exceptions import PaymentNotFound, RefundNotAllowed, ValidationError
from paybridge.domain.models import PaymentTransition, Refund, utc_now
from paybridge.domain.refund_policy import validate_refund

from .dto import RefundView
from .events import log_event
from .ports import PaymentRepository, RefundRepository


class RefundService:
    """Refund workflow: a customer *requests*; completion is either automatic or operator-gated.

    Only full refunds are supported. Completion atomically moves the payment to REFUNDED, writes
    the reverse-payment ledger entry and resolves the request, with audit evidence naming the
    authenticated actor.

    ``auto_approve=True`` is the behaviour AC-08 specifies (a request immediately yields the
    reverse entry and REFUNDED). Setting it to False (PAYBRIDGE_REFUND_AUTO_APPROVE=false) inserts
    a PENDING state that an operator must approve or reject.
    """

    def __init__(
        self, payments: PaymentRepository, refunds: RefundRepository, auto_approve: bool = True
    ) -> None:
        self._payments = payments
        self._refunds = refunds
        self._auto_approve = auto_approve

    def request_refund(
        self,
        payment_id: UUID,
        requested_amount: Decimal | None,
        actor: str,
        correlation_id: str,
        owner: str | None = None,
    ) -> RefundView:
        payment = self._payments.get_payment(payment_id)
        if owner is not None and payment.actor != owner:
            raise PaymentNotFound(str(payment_id))
        if requested_amount is not None and requested_amount != payment.amount:
            raise ValidationError("Only full refunds are supported")
        current = self._payments.get_current_state(payment_id)
        validate_refund(current, payment.amount, payment.amount)
        refund = Refund(
            uuid4(), payment_id, uuid4(), payment.amount, RefundStatus.PENDING, utc_now(), actor
        )
        # The unique index on original_payment_id makes the request itself idempotent.
        self._refunds.append_refund(refund, correlation_id)
        log_event("refund_requested", correlation_id, payment_id=payment_id, actor=actor)
        if self._auto_approve:
            # If completion fails the request stays PENDING and is visible in the ops refund queue.
            return self.approve_refund(refund.refund_id, actor, correlation_id)
        return self._view(refund)

    def approve_refund(self, refund_id: UUID, actor: str, correlation_id: str) -> RefundView:
        refund = self._pending(refund_id)
        transition = PaymentTransition(
            refund.original_payment_id,
            PaymentState.SETTLED,
            PaymentState.REFUNDED,
            utc_now(),
            actor,
            reason_code="REFUND",
            reason=str(refund.reverse_payment_id),
        )
        payment = self._payments.get_payment(refund.original_payment_id)
        self._refunds.complete_refund(refund, transition, payment.currency, correlation_id)
        log_event(
            "refund_completed", correlation_id, payment_id=refund.original_payment_id, actor=actor,
            reverse_payment_id=str(refund.reverse_payment_id),
        )
        return self._view(self._require(refund_id))

    def reject_refund(self, refund_id: UUID, reason: str, actor: str, correlation_id: str) -> RefundView:
        refund = self._pending(refund_id)
        self._refunds.fail_refund(refund, reason.strip() or "REJECTED", actor, correlation_id, utc_now())
        log_event("refund_rejected", correlation_id, payment_id=refund.original_payment_id, actor=actor)
        return self._view(self._require(refund_id))

    def get_for_payment(self, payment_id: UUID, owner: str | None = None) -> RefundView:
        payment = self._payments.get_payment(payment_id)
        if owner is not None and payment.actor != owner:
            raise PaymentNotFound(str(payment_id))
        refund = self._refunds.get_refund_for_payment(payment_id)
        if refund is None:
            raise PaymentNotFound(f"No refund for payment {payment_id}")
        return self._view(refund)

    def _require(self, refund_id: UUID) -> Refund:
        refund = self._refunds.get_refund(refund_id)
        if refund is None:
            raise PaymentNotFound(f"Refund {refund_id} not found")
        return refund

    def _pending(self, refund_id: UUID) -> Refund:
        refund = self._require(refund_id)
        if refund.status is not RefundStatus.PENDING:
            raise RefundNotAllowed("Refund has already been resolved")
        return refund

    @staticmethod
    def _view(refund: Refund) -> RefundView:
        return RefundView(
            refund_id=refund.refund_id,
            original_payment_id=refund.original_payment_id,
            reverse_payment_id=refund.reverse_payment_id,
            amount=refund.amount,
            status=refund.status,
            requested_at=refund.requested_at,
        )
