from decimal import Decimal
from itertools import product

import pytest

from paybridge.domain.enums import BeneficiaryType, Rail
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.rail_policy import eligible_rails, requires_reason_code, select_rail_for, validate_route


def test_rtgs_is_eligible_above_threshold():
    assert Rail.RTGS in eligible_rails(Decimal(200000), BeneficiaryType.CORPORATE)


def test_upi_is_eligible_for_retail():
    assert Rail.UPI in eligible_rails(Decimal(500), BeneficiaryType.RETAIL)


def test_route_validation_rejects_ineligible():
    with pytest.raises(ValidationError):
        validate_route(Rail.UPI, Decimal(150000), BeneficiaryType.CORPORATE)


def test_special_rails_require_reason():
    assert requires_reason_code(Rail.RTGS) and requires_reason_code(Rail.IMPS)



def test_validation_and_selection_never_drift():
    amounts = [Decimal(x) for x in ("1", "100000", "100000.01", "150000", "199999.99", "200000", "500000")]
    for amount, kind, urgent in product(amounts, BeneficiaryType, (False, True)):
        chosen, _reason = select_rail_for(amount, kind, urgent)
        validate_route(chosen, amount, kind, urgent)
        for other in Rail:
            if other is not chosen:
                with pytest.raises(ValidationError):
                    validate_route(other, amount, kind, urgent)


def test_urgent_retail_above_upi_ceiling_uses_imps():
    assert select_rail_for(Decimal(150000), BeneficiaryType.RETAIL, True)[0] is Rail.IMPS
    assert select_rail_for(Decimal(150000), BeneficiaryType.RETAIL, False)[0] is Rail.NEFT
