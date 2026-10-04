import pytest

from paybridge.domain.audit_policy import validate_actor, validate_correlation_id
from paybridge.domain.exceptions import ValidationError


def test_actor_trimmed():
    assert validate_actor(" actor ") == "actor"


def test_actor_required():
    with pytest.raises(ValidationError):
        validate_actor("")


def test_actor_length_bounded():
    with pytest.raises(ValidationError):
        validate_actor("x" * 81)


def test_correlation_trimmed():
    assert validate_correlation_id(" corr ") == "corr"


def test_correlation_required():
    with pytest.raises(ValidationError):
        validate_correlation_id("")


def test_correlation_length_bounded():
    with pytest.raises(ValidationError):
        validate_correlation_id("x" * 81)
