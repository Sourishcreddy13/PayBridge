import pytest

from paybridge.domain.exceptions import ValidationError
from paybridge.domain.narration_policy import normalize_narration


def test_normalization_collapses_whitespace():
    assert normalize_narration(" a  payment ") == "a payment"


def test_empty_narration_rejected():
    with pytest.raises(ValidationError):
        normalize_narration("   ")
