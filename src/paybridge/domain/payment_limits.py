from decimal import Decimal

from .enums import BeneficiaryType
from .exceptions import ValidationError

CUSTOMER_DAILY_LIMIT = Decimal("1000000.00")
CORPORATE_SINGLE_LIMIT = Decimal("10000000.00")


def validate_payment_limits(amount: Decimal, beneficiary_type: BeneficiaryType) -> None:
    if amount > CUSTOMER_DAILY_LIMIT and beneficiary_type is BeneficiaryType.RETAIL:
        raise ValidationError("Retail daily limit exceeded")
    if amount > CORPORATE_SINGLE_LIMIT:
        raise ValidationError("Payment exceeds maximum configured amount")


def is_high_value(amount: Decimal) -> bool:
    return amount >= Decimal("200000.00")
