from paybridge.domain.enums import PaymentState
from paybridge.domain.state_machine import ALLOWED_TRANSITIONS

def test_AC_04_no_outgoing_from_failed(): assert not ALLOWED_TRANSITIONS[PaymentState.FAILED]
def test_AC_04_no_outgoing_from_refunded(): assert not ALLOWED_TRANSITIONS[PaymentState.REFUNDED]
