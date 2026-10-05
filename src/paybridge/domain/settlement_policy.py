from collections.abc import Iterable
from datetime import date

from .enums import PaymentState
from .models import PaymentTransition


def eligible_for_settlement(transitions: Iterable[PaymentTransition], business_date: date) -> bool:
    """A payment belongs to a day's settlement iff it has a SETTLED transition on that day.

    Eligibility is derived from lifecycle history, not current state, so a payment that was
    settled and later refunded still appears in the settlement of the day it settled.
    """
    return any(
        t.to_state is PaymentState.SETTLED and t.at.date() == business_date for t in transitions
    )


def immutable_settlement_filename(business_date: date) -> str:
    return f"settlement-{business_date.isoformat()}.csv"
