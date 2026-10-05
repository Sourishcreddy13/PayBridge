from decimal import Decimal

import pytest

from paybridge.application.retry import RetryPolicy, execute_with_retry
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import RailResponse


def test_AC_05_transient_retries():
    results=[RailResponse('TRANSIENT_FAILURE',None,'TEMP',1), RailResponse('SUCCESS','ext',None,2)]
    out, attempts=execute_with_retry(lambda attempt: results[attempt-1], lambda r: r.outcome == 'TRANSIENT_FAILURE', RetryPolicy(3,0))
    assert out.outcome == 'SUCCESS' and attempts == 2

def test_AC_05_permanent_stops():
    out, attempts=execute_with_retry(lambda attempt: RailResponse('PERMANENT_FAILURE',None,'DENIED',attempt), lambda r: r.outcome == 'TRANSIENT_FAILURE', RetryPolicy(3,0))
    assert out.reason_code == 'DENIED' and attempts == 1






@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0},
        {"max_attempts": -1},
        {"max_attempts": 11},
        {"max_attempts": True},
        {"base_delay_seconds": Decimal(-1)},
        {"base_delay_seconds": Decimal("NaN")},
        {"multiplier": Decimal("0.5")},
    ],
)
def test_AC_05_invalid_retry_policy_fails_closed(kwargs):
    with pytest.raises(ValidationError):
        RetryPolicy(**kwargs)


def test_AC_05_exhausted_attempts_return_last_result():
    out, attempts = execute_with_retry(
        lambda a: RailResponse('TRANSIENT_FAILURE', None, 'TEMP', a),
        lambda r: r.outcome == 'TRANSIENT_FAILURE',
        RetryPolicy(2, 0),
    )
    assert attempts == 2 and out.attempt == 2


def test_AC_05_backoff_delays_grow(monkeypatch):
    slept = []
    monkeypatch.setattr("paybridge.application.retry.sleep", slept.append)
    execute_with_retry(
        lambda a: RailResponse('TRANSIENT_FAILURE', None, 'TEMP', a),
        lambda r: True,
        RetryPolicy(3, Decimal("0.5"), Decimal(2)),
    )
    assert slept == [0.5, 1.0]
