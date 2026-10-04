from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import Beneficiary, Payment


def test_invalid_beneficiary_account_rejected():
    with pytest.raises(ValidationError):
        Beneficiary("123", "ABCD0123456", BeneficiaryType.RETAIL, "Demo")


def test_invalid_ifsc_rejected():
    with pytest.raises(ValidationError):
        Beneficiary("123456789012", "BAD", BeneficiaryType.RETAIL, "Demo")


def test_invalid_name_rejected():
    with pytest.raises(ValidationError):
        Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "")


def test_naive_payment_timestamp_rejected():
    with pytest.raises(ValidationError):
        Payment(
            uuid4(),
            Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo"),
            Decimal(1),
            "demo",
            "model-ts-01",
            "INR",
            datetime.now(tz=UTC).replace(tzinfo=None),
            "actor",
        )
