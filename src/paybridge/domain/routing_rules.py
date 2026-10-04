from decimal import Decimal

from .enums import BeneficiaryType, Rail
from .models import Beneficiary

RTGS_MINIMUM = Decimal("200000.00")
UPI_RETAIL_MAXIMUM = Decimal("100000.00")


def select_rail(amount: Decimal, beneficiary: Beneficiary, urgent: bool = False) -> tuple[Rail, str]:
    """Select a rail using deterministic rules from the business brief."""
    if amount >= RTGS_MINIMUM:
        return Rail.RTGS, "amount >= ₹200,000"
    if beneficiary.beneficiary_type is BeneficiaryType.RETAIL and amount <= UPI_RETAIL_MAXIMUM:
        return Rail.UPI, "retail beneficiary and amount <= ₹100,000"
    if urgent and beneficiary.beneficiary_type is BeneficiaryType.RETAIL:
        return Rail.IMPS, "urgent eligible retail payment outside UPI ceiling"
    return Rail.NEFT, "default rail for remaining eligible payments"
