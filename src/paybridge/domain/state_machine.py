from .enums import PaymentState
from .exceptions import InvalidPaymentStateException

ALLOWED_TRANSITIONS: dict[PaymentState, frozenset[PaymentState]] = {
    PaymentState.PENDING: frozenset({PaymentState.PROCESSING, PaymentState.FAILED}),
    PaymentState.PROCESSING: frozenset({PaymentState.SETTLED, PaymentState.FAILED}),
    PaymentState.SETTLED: frozenset({PaymentState.REFUNDED}),
    PaymentState.FAILED: frozenset(),
    PaymentState.REFUNDED: frozenset(),
}


def validate_transition(current: PaymentState, requested: PaymentState) -> None:
    if requested not in ALLOWED_TRANSITIONS[current]:
        raise InvalidPaymentStateException(current.value, requested.value)


def next_state(current: PaymentState, requested: PaymentState) -> PaymentState:
    validate_transition(current, requested)
    return requested
