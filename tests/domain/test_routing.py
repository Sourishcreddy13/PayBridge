from decimal import Decimal

from paybridge.domain.enums import BeneficiaryType, Rail
from paybridge.domain.models import Beneficiary
from paybridge.domain.rail_policy import select_rail


def beneficiary(kind): return Beneficiary('123456789012', 'ABCD0123456', kind, 'Demo User')


def test_AC_03_rtgs_threshold():
    rail, _ = select_rail(Decimal(200000), beneficiary(BeneficiaryType.CORPORATE))
    assert rail is Rail.RTGS


def test_AC_03_upi_retail_ceiling():
    rail, _ = select_rail(Decimal(100000), beneficiary(BeneficiaryType.RETAIL))
    assert rail is Rail.UPI


def test_AC_03_neft_default():
    rail, _ = select_rail(Decimal(150000), beneficiary(BeneficiaryType.CORPORATE))
    assert rail is Rail.NEFT
