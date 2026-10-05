import pytest

from paybridge.domain.enums import RailOutcome
from paybridge.domain.exceptions import ValidationError
from paybridge.infrastructure.rail_adapters import RailScript


def test_empty_rail_script_is_rejected():
    with pytest.raises(ValidationError):
        RailScript(())


def test_non_outcome_values_are_rejected():
    with pytest.raises(ValidationError):
        RailScript(("SUCCESS",))  # type: ignore[arg-type]


def test_valid_script_is_accepted():
    assert RailScript((RailOutcome.SUCCESS,)).outcomes
