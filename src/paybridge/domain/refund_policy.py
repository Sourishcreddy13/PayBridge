from decimal import Decimal

from .enums import PaymentState
from .exceptions import RefundNotAllowed, ValidationError


def validate_refund(state: PaymentState, original_amount: Decimal, requested_amount: Decimal) -> None:
    if state is not PaymentState.SETTLED:
        raise RefundNotAllowed("Only SETTLED payments can be refunded")
    if requested_amount <= Decimal("0"):
        raise ValidationError("Refund amount must be positive")
    if requested_amount > original_amount:
        raise ValidationError("Refund cannot exceed original payment amount")
