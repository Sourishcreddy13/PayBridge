from uuid import uuid4
from paybridge.application.retry_pipeline_service import RetryPipelineService
from paybridge.application.retry import RetryPolicy
from paybridge.domain.models import RailResponse

class Payments:
    def get_payment(self,payment_id): return object()
class Attempts:
    def list_attempts(self,payment_id): return [{'attempt':'1','outcome':'SUCCESS'}]

def test_retry_pipeline_reads_attempts():
    pid=uuid4(); service=RetryPipelineService(Payments(),Attempts()); assert service.attempts_for_payment(pid)[0]['outcome']=='SUCCESS'
def test_retry_pipeline_detects_transient(): assert RetryPipelineService.should_retry(RailResponse('TRANSIENT_FAILURE',None,'TEMP',1))
def test_retry_pipeline_does_not_retry_success(): assert not RetryPipelineService.should_retry(RailResponse('SUCCESS','x',None,1))
def test_retry_policy_validation(): RetryPipelineService.validate_policy(RetryPolicy())
