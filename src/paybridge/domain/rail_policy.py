from decimal import Decimal

from .enums import BeneficiaryType, Rail
from .exceptions import ValidationError

UPI_MAX = Decimal("100000.00")
IMPS_MAX = Decimal("200000.00")
RTGS_MIN = Decimal("200000.00")


def eligible_rails(amount: Decimal, beneficiary_type: BeneficiaryType, urgent: bool = False) -> frozenset[Rail]:
    rails: set[Rail] = {Rail.NEFT}
    if beneficiary_type is BeneficiaryType.RETAIL and amount <= UPI_MAX:
        rails.add(Rail.UPI)
    if amount < RTGS_MIN:
        rails.add(Rail.IMPS)
    else:
        rails.add(Rail.RTGS)
    if urgent and beneficiary_type is BeneficiaryType.RETAIL and amount < IMPS_MAX:
        rails.add(Rail.IMPS)
    return frozenset(rails)


def validate_route(rail: Rail, amount: Decimal, beneficiary_type: BeneficiaryType, urgent: bool = False) -> None:
    if rail not in eligible_rails(amount, beneficiary_type, urgent):
        raise ValidationError(f"Rail {rail.value} is not eligible for this payment")


def requires_reason_code(rail: Rail) -> bool:
    return rail in {Rail.RTGS, Rail.IMPS}
