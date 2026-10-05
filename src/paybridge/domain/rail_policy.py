"""Canonical rail policy: the single source of truth for rail selection and eligibility."""

from decimal import Decimal

from .enums import BeneficiaryType, Rail
from .exceptions import ValidationError
from .models import Beneficiary

RTGS_MINIMUM = Decimal("200000.00")
UPI_RETAIL_MAXIMUM = Decimal("100000.00")


def select_rail_for(
    amount: Decimal, beneficiary_type: BeneficiaryType, urgent: bool = False
) -> tuple[Rail, str]:
    """Deterministically choose the one rail a payment must use, with the reason."""
    if amount >= RTGS_MINIMUM:
        return Rail.RTGS, "amount >= ₹200,000"
    if beneficiary_type is BeneficiaryType.RETAIL and amount <= UPI_RETAIL_MAXIMUM:
        return Rail.UPI, "retail beneficiary and amount <= ₹100,000"
    if urgent and beneficiary_type is BeneficiaryType.RETAIL:
        return Rail.IMPS, "urgent eligible retail payment outside UPI ceiling"
    return Rail.NEFT, "default rail for remaining eligible payments"


def select_rail(
    amount: Decimal, beneficiary: Beneficiary, urgent: bool = False
) -> tuple[Rail, str]:
    return select_rail_for(amount, beneficiary.beneficiary_type, urgent)


def eligible_rails(
    amount: Decimal, beneficiary_type: BeneficiaryType, urgent: bool = False
) -> frozenset[Rail]:
    """A route is eligible only if the selection policy would choose it."""
    return frozenset({select_rail_for(amount, beneficiary_type, urgent)[0]})


def validate_route(
    rail: Rail, amount: Decimal, beneficiary_type: BeneficiaryType, urgent: bool = False
) -> None:
    if rail not in eligible_rails(amount, beneficiary_type, urgent):
        raise ValidationError(f"Rail {rail.value} is not eligible for this payment")


def requires_reason_code(rail: Rail) -> bool:
    return rail in {Rail.RTGS, Rail.IMPS}
