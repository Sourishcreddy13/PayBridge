from decimal import Decimal

from .exceptions import ValidationError

SUPPORTED_CURRENCY = "INR"
MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("100000000.00")


def validate_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if normalized != SUPPORTED_CURRENCY:
        raise ValidationError("Only INR is supported")
    return normalized


def validate_amount_band(amount: Decimal) -> None:
    if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        raise ValidationError("Amount is outside the supported business range")
