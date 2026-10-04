from uuid import UUID

from paybridge.domain.models import PaymentTransition
from paybridge.application.ports import PaymentRepository


class TimelineService:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def get_timeline(self, payment_id: UUID) -> list[PaymentTransition]:
        return self._repository.list_transitions(payment_id)

    @staticmethod
    def summarize(transitions: list[PaymentTransition]) -> list[str]:
        summary: list[str] = []
        for transition in transitions:
            reason = f" ({transition.reason_code})" if transition.reason_code else ""
            summary.append(f"{transition.from_state.value} -> {transition.to_state.value}{reason}")
        return summary
