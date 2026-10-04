import pytest

from paybridge.domain.beneficiary_policy import beneficiary_key, validate_beneficiary
from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import Beneficiary


def test_beneficiary_key_uses_last_four():
    beneficiary = Beneficiary(
        "123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo User"
    )
    assert beneficiary_key(beneficiary).endswith(":RETAIL")


def test_supported_beneficiary_passes():
    validate_beneficiary(
        Beneficiary(
            "123456789012", "WXYZ0987654", BeneficiaryType.CORPORATE, "Demo User"
        )
    )


def test_unknown_bank_rejected():
    with pytest.raises(ValidationError):
        validate_beneficiary(
            Beneficiary(
                "123456789012", "XXXX0987654", BeneficiaryType.RETAIL, "Demo User"
            )
        )
