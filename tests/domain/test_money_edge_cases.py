from decimal import Decimal

import pytest

from paybridge.domain.exceptions import ValidationError
from paybridge.domain.money import format_amount, parse_amount


def test_amount_from_integer(): assert parse_amount(10)==Decimal('10.00')
def test_amount_from_decimal(): assert parse_amount(Decimal('10.12'))==Decimal('10.12')
def test_non_numeric_rejected():
    with pytest.raises(ValidationError): parse_amount('not-money')
def test_infinite_rejected():
    with pytest.raises(ValidationError): parse_amount('Infinity')
def test_format_uses_two_decimals(): assert format_amount(Decimal(10))=='10.00'
