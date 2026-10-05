import pytest

from paybridge.domain.exceptions import ValidationError
from paybridge.domain.money import format_amount, parse_amount


def test_decimal_rounding():
    assert format_amount(parse_amount('10.005')) == '10.01'


def test_zero_rejected():
    with pytest.raises(ValidationError): parse_amount('0')


def test_negative_rejected():
    with pytest.raises(ValidationError): parse_amount('-1')
