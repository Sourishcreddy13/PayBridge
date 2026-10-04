from paybridge.application.retry import RetryPolicy, execute_with_retry
from paybridge.domain.models import RailResponse

def test_AC_05_transient_retries():
    results=[RailResponse('TRANSIENT_FAILURE',None,'TEMP',1), RailResponse('SUCCESS','ext',None,2)]
    out, attempts=execute_with_retry(lambda attempt: results[attempt-1], lambda r: r.outcome == 'TRANSIENT_FAILURE', RetryPolicy(3,0))
    assert out.outcome == 'SUCCESS' and attempts == 2

def test_AC_05_permanent_stops():
    out, attempts=execute_with_retry(lambda attempt: RailResponse('PERMANENT_FAILURE',None,'DENIED',attempt), lambda r: r.outcome == 'TRANSIENT_FAILURE', RetryPolicy(3,0))
    assert out.reason_code == 'DENIED' and attempts == 1
