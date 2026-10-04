from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .exceptions import ValidationError

CURRENCY_SCALE = Decimal("0.01")


def parse_amount(value: str | Decimal | int) -> Decimal:
    """Parse and normalize money using fixed-point arithmetic."""
    try:
        amount = Decimal(str(value)).quantize(CURRENCY_SCALE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("Invalid monetary value") from exc
    if amount <= Decimal("0"):
        raise ValidationError("Amount must be greater than zero")
    if not amount.is_finite():
        raise ValidationError("Amount must be finite")
    return amount


def format_amount(value: Decimal) -> str:
    """Return a canonical two-decimal monetary representation."""
    return value.quantize(CURRENCY_SCALE, rounding=ROUND_HALF_UP).to_eng_string()
