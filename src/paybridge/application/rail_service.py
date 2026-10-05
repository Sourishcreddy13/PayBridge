from collections.abc import Mapping
from uuid import UUID

from paybridge.domain.enums import RailOutcome
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import RailResponse

from .events import log_event
from .ports import PaymentRepository, RailAdapter, RoutingRepository
from .retry import RetryPolicy, execute_with_retry


class RailService:
    def __init__(
        self,
        repository: PaymentRepository,
        adapters: Mapping[str, RailAdapter],
        routes: RoutingRepository | None = None,
    ) -> None:
        self._repository = repository
        self._adapters = adapters
        self._routes = routes

    def submit(
        self,
        payment_id: UUID,
        actor: str,
        correlation_id: str,
        policy: RetryPolicy,
    ) -> tuple[RailResponse, int]:
        payment = self._repository.get_payment(payment_id)
        route = self._resolve_route(payment_id)
        adapter = self._adapters.get(route)
        if adapter is None:
            raise ValidationError(f"No rail adapter configured for {route}")

        def call(attempt: int) -> RailResponse:
            response = adapter.submit(payment, attempt)
            log_event(
                "rail_attempt", correlation_id, payment_id=payment_id, actor=actor,
                rail=route, attempt=attempt, outcome=response.outcome,
            )
            return response

        return execute_with_retry(
            call, lambda result: result.outcome == RailOutcome.TRANSIENT_FAILURE.value, policy
        )

    def _resolve_route(self, payment_id: UUID) -> str:
        if self._routes is None:
            raise ValidationError("Rail service has no routing repository")
        route = self._routes.get_route(payment_id)
        if route is None:
            raise ValidationError("Payment has no persisted routing decision")
        return route.value
