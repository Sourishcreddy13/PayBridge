from decimal import Decimal
import pytest
from paybridge.domain.currency_policy import validate_amount_band, validate_currency
from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.payment_limits import is_high_value, validate_payment_limits


def test_currency_is_normalized(): assert validate_currency('inr')=='INR'
def test_currency_is_restricted():
    with pytest.raises(Exception): validate_currency('USD')
def test_high_value_flag(): assert is_high_value(Decimal('200000'))
def test_retail_limit():
    with pytest.raises(Exception): validate_payment_limits(Decimal('1000001'),BeneficiaryType.RETAIL)
def test_amount_upper_bound():
    with pytest.raises(Exception): validate_amount_band(Decimal('100000000.01'))
