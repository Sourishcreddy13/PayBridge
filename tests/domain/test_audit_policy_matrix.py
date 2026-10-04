import pytest

from paybridge.domain.audit_policy import validate_actor, validate_correlation_id
from paybridge.domain.exceptions import ValidationError


@pytest.mark.parametrize("value", ["actor-a", "ops-user", "admin-user", "customer-user"])
def test_actor_accepts_valid_values(value):
    assert validate_actor(value) == value


@pytest.mark.parametrize("value", ["corr-1", "corr-2", "request-abcdef"])
def test_correlation_accepts_valid_values(value):
    assert validate_correlation_id(value) == value


@pytest.mark.parametrize("value", ["", "   ", "x" * 81])
def test_actor_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        validate_actor(value)


@pytest.mark.parametrize("value", ["", "   ", "x" * 81])
def test_correlation_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        validate_correlation_id(value)
