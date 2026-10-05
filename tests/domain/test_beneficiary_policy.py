import pytest

from paybridge.domain.beneficiary_policy import validate_beneficiary
from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import Beneficiary


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
