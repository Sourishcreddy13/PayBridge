from uuid import UUID

from paybridge.domain.models import RailResponse
from .ports import PaymentRepository, RailAdapter
from .retry import RetryPolicy, execute_with_retry


class RailService:
    def __init__(self, repository: PaymentRepository, adapters: dict[str, RailAdapter]) -> None:
        self._repository = repository
        self._adapters = adapters

    def submit(self, payment_id: UUID, actor: str, correlation_id: str, policy: RetryPolicy) -> tuple[RailResponse, int]:
        payment = self._repository.get_payment(payment_id)
        state = self._repository.get_current_state(payment_id)
        route = self._resolve_route(payment_id)
        adapter = self._adapters[route]
        def call(attempt: int) -> RailResponse:
            return adapter.submit(payment, attempt)
        response, attempts = execute_with_retry(call, lambda result: result.outcome == "TRANSIENT_FAILURE", policy)
        return response, attempts

    def _resolve_route(self, payment_id: UUID) -> str:
        from paybridge.domain.enums import Rail
        # Routing is persisted by the routing repository; PaymentService guarantees it before processing.
        # This helper is replaced by the injected service with a simple adapter map lookup using repository state.
        route = getattr(self._repository, "get_route_for_payment", lambda _: None)(payment_id)
        if route is None:
            route = Rail.NEFT.value
        return route
