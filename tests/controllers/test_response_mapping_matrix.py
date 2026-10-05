
from paybridge.controllers.response_mapper import map_domain_error
from paybridge.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    InvalidPaymentStateException,
    PaymentNotFound,
    RefundNotAllowed,
    SettlementAlreadyExists,
    ValidationError,
)


def test_authentication_maps_to_401(): assert map_domain_error(AuthenticationError('x')).status_code==401
def test_authorization_maps_to_403(): assert map_domain_error(AuthorizationError('x')).status_code==403
def test_payment_not_found_maps_to_404(): assert map_domain_error(PaymentNotFound('x')).status_code==404
def test_invalid_transition_maps_to_409(): assert map_domain_error(InvalidPaymentStateException('PENDING','SETTLED')).status_code==409
def test_refund_policy_maps_to_409(): assert map_domain_error(RefundNotAllowed('x')).status_code==409
def test_settlement_conflict_maps_to_409(): assert map_domain_error(SettlementAlreadyExists('x')).status_code==409
def test_validation_maps_to_422(): assert map_domain_error(ValidationError('x')).status_code==422
def test_domain_fallback_maps_to_400(): assert map_domain_error(DomainError('x')).status_code==400
