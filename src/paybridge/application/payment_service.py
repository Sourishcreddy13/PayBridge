from uuid import UUID, uuid4

from paybridge.domain.enums import PaymentState, RailOutcome
from paybridge.domain.models import Beneficiary, Payment, PaymentTransition, utc_now
from paybridge.domain.pii_policy import mask_account_number, mask_ifsc
from paybridge.domain.state_machine import validate_transition

from .audit import AuditService
from .dto import CreatePaymentInput, PaymentListItem, PaymentView
from .ports import PaymentRepository, RoutingRepository
from .rail_service import RailService
from .retry import RetryPolicy
from .routing_service import RoutingService


class PaymentService:
    def __init__(
        self,
        repository: PaymentRepository,
        routing_repository: RoutingRepository,
        routing_service: RoutingService,
        rail_service: RailService,
        audit: AuditService,
        retry_policy: RetryPolicy,
    ) -> None:
        self._repository = repository
        self._routing_repository = routing_repository
        self._routing_service = routing_service
        self._rail_service = rail_service
        self._audit = audit
        self._retry_policy = retry_policy

    def create_payment(self, command: CreatePaymentInput, actor: str, correlation_id: str) -> PaymentView:
        payment_id = uuid4()
        payment = Payment(
            payment_id=payment_id,
            beneficiary=Beneficiary(**command.beneficiary.model_dump()),
            amount=command.amount,
            narration=command.narration.strip(),
            idempotency_key=command.idempotency_key,
            currency="INR",
            created_at=utc_now(),
            actor=actor,
        )
        created, original_id = self._repository.reserve_and_append_payment(payment)
        if not created:
            return self.get_payment(original_id)
        self._audit.record_event(
            "PAYMENT_CREATED", actor, correlation_id, payment_id, {"initial_state": PaymentState.PENDING.value}
        )
        decision = self._routing_service.route(payment, actor, correlation_id, urgent=command.urgent)
        self._routing_repository.append_decision(decision)
        self._audit.record_routing(decision, correlation_id)
        return self.get_payment(payment_id)

    def process_payment(self, payment_id: UUID, actor: str, correlation_id: str) -> PaymentView:
        current = self._repository.get_current_state(payment_id)
        validate_transition(current, PaymentState.PROCESSING)
        processing = PaymentTransition(payment_id, current, PaymentState.PROCESSING, utc_now(), actor)
        self._repository.append_transition(processing)
        self._audit.record_transition(processing, correlation_id)
        response, attempts = self._rail_service.submit(payment_id, actor, correlation_id, self._retry_policy)
        latest = self._repository.get_current_state(payment_id)
        if response.outcome == RailOutcome.SUCCESS.value:
            transition = PaymentTransition(payment_id, latest, PaymentState.SETTLED, utc_now(), actor)
        else:
            transition = PaymentTransition(
                payment_id,
                latest,
                PaymentState.FAILED,
                utc_now(),
                actor,
                reason_code=response.reason_code or "RAIL_FAILURE",
                reason=f"rail failed after {attempts} attempt(s)",
            )
        validate_transition(latest, transition.to_state)
        self._repository.append_transition(transition)
        self._audit.record_transition(transition, correlation_id)
        return self.get_payment(payment_id)

    def get_payment(self, payment_id: UUID) -> PaymentView:
        payment = self._repository.get_payment(payment_id)
        state = self._repository.get_current_state(payment_id)
        rail = self._routing_repository.get_route(payment_id)
        return PaymentView(
            payment_id=payment.payment_id,
            state=state,
            amount=payment.amount,
            currency=payment.currency,
            narration=payment.narration,
            beneficiary_name=payment.beneficiary.name,
            masked_account_number=mask_account_number(payment.beneficiary.account_number),
            masked_ifsc=mask_ifsc(payment.beneficiary.ifsc),
            rail=rail,
            created_at=payment.created_at,
        )

    def history(self, actor: str) -> list[PaymentListItem]:
        return [
            PaymentListItem(
                payment_id=p.payment_id,
                state=self._repository.get_current_state(p.payment_id),
                amount=p.amount,
                currency=p.currency,
                rail=self._routing_repository.get_route(p.payment_id),
                created_at=p.created_at,
            )
            for p in self._repository.list_payments(actor=actor)
        ]
