
from paybridge.domain.models import Payment, RoutingDecision, utc_now
from paybridge.domain.rail_policy import select_rail


class RoutingService:
    def route(self, payment: Payment, actor: str, correlation_id: str, urgent: bool = False) -> RoutingDecision:
        rail, reason = select_rail(payment.amount, payment.beneficiary, urgent=urgent)
        return RoutingDecision(payment.payment_id, rail, reason, utc_now(), actor)
