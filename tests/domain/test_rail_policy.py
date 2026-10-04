from decimal import Decimal
import pytest
from paybridge.domain.enums import BeneficiaryType, Rail
from paybridge.domain.rail_policy import eligible_rails, requires_reason_code, validate_route

def test_rtgs_is_eligible_above_threshold(): assert Rail.RTGS in eligible_rails(Decimal('200000'),BeneficiaryType.CORPORATE)
def test_upi_is_eligible_for_retail(): assert Rail.UPI in eligible_rails(Decimal('500'),BeneficiaryType.RETAIL)
def test_route_validation_rejects_ineligible():
    with pytest.raises(Exception): validate_route(Rail.UPI,Decimal('150000'),BeneficiaryType.CORPORATE)
def test_special_rails_require_reason(): assert requires_reason_code(Rail.RTGS) and requires_reason_code(Rail.IMPS)
