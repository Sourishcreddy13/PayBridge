from decimal import Decimal
from uuid import UUID

from .exceptions import ValidationError


def refund_reference(original_payment_id: UUID, amount: Decimal) -> str:
    normalized = amount.quantize(Decimal("0.01"))
    return f"RF-{str(original_payment_id)[:12]}-{normalized}"


def validate_refund_reference(reference: str) -> str:
    value = reference.strip()
    if not value.startswith("RF-") or len(value) > 64:
        raise ValidationError("Invalid refund reference")
    return value
