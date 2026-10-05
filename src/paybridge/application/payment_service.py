import logging
from uuid import UUID, uuid4

from paybridge.domain.enums import PaymentState, RailOutcome
from paybridge.domain.exceptions import PaymentNotFound
from paybridge.domain.models import Beneficiary, Payment, PaymentTransition, utc_now
from paybridge.domain.pii_policy import mask_account_number, mask_ifsc

from .audit import AuditService
from .dto import CreatePaymentInput, PaymentListItem, PaymentView
from .events import log_event
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
        decision = self._routing_service.route(payment, actor, correlation_id, urgent=command.urgent)
        # Payment, idempotency key, routing decision and their audit events commit together.
        created, original_id = self._repository.reserve_and_append_payment(payment, decision, correlation_id)
        if not created:
            log_event("payment_replayed", correlation_id, payment_id=original_id, actor=actor)
            return self.get_payment(original_id)
        log_event(
            "payment_created", correlation_id, payment_id=payment_id, actor=actor,
            rail=decision.rail.value,
        )
        return self.get_payment(payment_id)

    def process_payment(self, payment_id: UUID, actor: str, correlation_id: str) -> PaymentView:
        """Execute a PENDING payment on its rail.

        The PENDING->PROCESSING reservation is atomic at the persistence boundary; a concurrent
        or repeated caller fails with InvalidPaymentStateException before touching the rail.
        """
        self._repository.get_payment(payment_id)
        processing = PaymentTransition(
            payment_id, PaymentState.PENDING, PaymentState.PROCESSING, utc_now(), actor
        )
        self._repository.append_transition(processing, correlation_id)
        log_event(
            "payment_processing", correlation_id, payment_id=payment_id, actor=actor,
            to_state=PaymentState.PROCESSING.value,
        )
        try:
            response, attempts = self._rail_service.submit(
                payment_id, actor, correlation_id, self._retry_policy
            )
        except Exception:
            # Never leave a payment stranded in PROCESSING because an adapter blew up.
            log_event(
                "rail_error", correlation_id, payment_id=payment_id, actor=actor, level=logging.ERROR
            )
            self._finish(
                payment_id, actor, correlation_id, PaymentState.FAILED,
                reason_code="RAIL_ERROR", reason="rail adapter raised an unexpected error",
            )
            return self.get_payment(payment_id)
        if response.outcome == RailOutcome.SUCCESS.value:
            self._finish(payment_id, actor, correlation_id, PaymentState.SETTLED)
        else:
            self._finish(
                payment_id, actor, correlation_id, PaymentState.FAILED,
                reason_code=response.reason_code or "RAIL_FAILURE",
                reason=f"rail failed after {attempts} attempt(s)",
            )
        return self.get_payment(payment_id)

    def _finish(
        self,
        payment_id: UUID,
        actor: str,
        correlation_id: str,
        to_state: PaymentState,
        reason_code: str | None = None,
        reason: str | None = None,
    ) -> None:
        transition = PaymentTransition(
            payment_id, PaymentState.PROCESSING, to_state, utc_now(), actor, reason_code, reason
        )
        # Transition and its audit event are written in one transaction.
        self._repository.append_transition(transition, correlation_id)
        log_event(
            "payment_" + to_state.value.lower(), correlation_id, payment_id=payment_id, actor=actor,
            to_state=to_state.value, reason_code=reason_code or "",
        )

    def require_access(self, payment_id: UUID, owner: str | None) -> Payment:
        """Object-level authorization. ``owner`` is the customer subject, or None for staff.

        A payment owned by someone else is reported as not found so ids cannot be probed.
        """
        payment = self._repository.get_payment(payment_id)
        if owner is not None and payment.actor != owner:
            raise PaymentNotFound(str(payment_id))
        return payment

    def get_payment(self, payment_id: UUID, owner: str | None = None) -> PaymentView:
        payment = self.require_access(payment_id, owner)
        state = self._repository.get_current_state(payment_id)
        latest = self._repository.latest_transition(payment_id)
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
            reason_code=latest.reason_code if latest is not None else None,
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
