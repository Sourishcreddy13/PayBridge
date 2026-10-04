from uuid import UUID

from paybridge.domain.models import RailResponse
from paybridge.application.ports import PaymentRepository, RailAttemptRepository
from paybridge.application.retry import RetryPolicy, execute_with_retry


class RetryPipelineService:
    """Small application service used by ops views to explain retry activity."""

    def __init__(self, payments: PaymentRepository, attempts: RailAttemptRepository) -> None:
        self._payments = payments
        self._attempts = attempts

    def attempts_for_payment(self, payment_id: UUID) -> list[dict[str, str]]:
        self._payments.get_payment(payment_id)
        return self._attempts.list_attempts(payment_id)

    @staticmethod
    def should_retry(response: RailResponse) -> bool:
        return response.outcome == "TRANSIENT_FAILURE"

    @staticmethod
    def validate_policy(policy: RetryPolicy) -> None:
        if policy.max_attempts < 1:
            raise ValueError("Retry policy must allow at least one attempt")
