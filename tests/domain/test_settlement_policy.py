from datetime import UTC, date, datetime
from uuid import uuid4

from paybridge.domain.enums import PaymentState
from paybridge.domain.models import PaymentTransition
from paybridge.domain.settlement_policy import (
    eligible_for_settlement,
    immutable_settlement_filename,
)

DAY = date(2026, 10, 4)


def transition(to_state, day=DAY):
    return PaymentTransition(uuid4(), PaymentState.PROCESSING, to_state, datetime(day.year, day.month, day.day, 9, tzinfo=UTC), "a")


def test_AC_07_settled_on_business_date_eligible():
    assert eligible_for_settlement([transition(PaymentState.SETTLED)], DAY)


def test_AC_07_pending_not_eligible():
    assert not eligible_for_settlement([], DAY)


def test_AC_07_settled_then_refunded_remains_eligible():
    history = [transition(PaymentState.SETTLED), transition(PaymentState.REFUNDED)]
    assert eligible_for_settlement(history, DAY)


def test_AC_07_settled_other_day_not_eligible():
    assert not eligible_for_settlement([transition(PaymentState.SETTLED, date(2026, 10, 3))], DAY)


def test_AC_07_filename():
    assert immutable_settlement_filename(DAY) == "settlement-2026-10-04.csv"
