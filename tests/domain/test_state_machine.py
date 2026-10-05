import pytest

from paybridge.domain.enums import PaymentState
from paybridge.domain.exceptions import InvalidPaymentStateException
from paybridge.domain.state_machine import validate_transition


def test_AC_04_valid_pending_processing(): validate_transition(PaymentState.PENDING, PaymentState.PROCESSING)

def test_AC_04_valid_processing_settled(): validate_transition(PaymentState.PROCESSING, PaymentState.SETTLED)

def test_AC_04_invalid_pending_settled():
    with pytest.raises(InvalidPaymentStateException): validate_transition(PaymentState.PENDING, PaymentState.SETTLED)

def test_AC_04_settled_cannot_failed():
    with pytest.raises(InvalidPaymentStateException): validate_transition(PaymentState.SETTLED, PaymentState.FAILED)
