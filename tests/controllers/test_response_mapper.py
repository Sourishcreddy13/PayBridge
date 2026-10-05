from paybridge.controllers.response_mapper import map_domain_error, safe_error_payload
from paybridge.domain.exceptions import DomainError, PaymentNotFound


def test_not_found_maps_to_404(): assert map_domain_error(PaymentNotFound('x')).status_code==404
def test_unknown_domain_error_is_sanitized():
    err=DomainError('safe'); assert safe_error_payload(err)=={'error':'safe'}
def test_unknown_error_is_generic(): assert safe_error_payload(RuntimeError('secret'))=={'error':'internal_error'}
