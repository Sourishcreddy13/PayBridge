from uuid import UUID

from paybridge.domain.models import PaymentTransition, RoutingDecision
from .ports import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

    def record_transition(self, transition: PaymentTransition, correlation_id: str) -> None:
        self._repository.append_transition_audit(transition, correlation_id)

    def record_routing(self, decision: RoutingDecision, correlation_id: str) -> None:
        self._repository.append_routing_audit(decision, correlation_id)

    def record_event(self, event_type: str, actor: str, correlation_id: str, payment_id: UUID | None, payload: dict[str, str]) -> None:
        self._repository.append_event(event_type, actor, correlation_id, payment_id, payload)
