from uuid import UUID, uuid4
from paybridge.domain.enums import PaymentState, RefundStatus
from paybridge.domain.models import Payment, PaymentTransition, Refund, utc_now
from paybridge.domain.refund_policy import validate_refund

from .audit import AuditService
from .dto import RefundView
from .ports import PaymentRepository, RefundRepository


class RefundService:
    def __init__(self, payments: PaymentRepository, refunds: RefundRepository, audit: AuditService) -> None:
        self._payments = payments
        self._refunds = refunds
        self._audit = audit

    def request_refund(self, payment_id: UUID, requested_amount, actor: str, correlation_id: str) -> RefundView:
        payment = self._payments.get_payment(payment_id)
        current = self._payments.get_current_state(payment_id)
        amount = requested_amount if requested_amount is not None else payment.amount
        validate_refund(current, payment.amount, amount)
        reverse_id = uuid4()
        refund = Refund(uuid4(), payment_id, reverse_id, amount, RefundStatus.COMPLETED, utc_now(), actor)
        self._refunds.append_refund(refund)
        transition = PaymentTransition(payment_id, current, PaymentState.REFUNDED, utc_now(), actor, reason_code="REFUND", reason=str(reverse_id))
        self._payments.append_transition(transition)
        self._audit.record_transition(transition, correlation_id)
        self._audit.record_event("REFUND_CREATED", actor, correlation_id, payment_id, {"reverse_payment_id": str(reverse_id)})
        return RefundView(refund_id=refund.refund_id, original_payment_id=refund.original_payment_id, reverse_payment_id=refund.reverse_payment_id, amount=refund.amount, status=refund.status, requested_at=refund.requested_at)
