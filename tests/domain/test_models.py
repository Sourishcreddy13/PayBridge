from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import Beneficiary, Payment


def test_AC_01_payment_is_immutable():
    payment = Payment(
        uuid4(),
        Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo"),
        Decimal(1),
        "demo",
        "models-idem-1",
        "INR",
        datetime.now(tz=UTC),
        "actor",
    )
    with pytest.raises(FrozenInstanceError):
        payment.amount = Decimal(2)


def test_AC_01_bad_currency():
    with pytest.raises(ValidationError):
        Payment(
            uuid4(),
            Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo"),
            Decimal(1),
            "demo",
            "models-idem-2",
            "USD",
            datetime.now(tz=UTC),
            "actor",
        )
