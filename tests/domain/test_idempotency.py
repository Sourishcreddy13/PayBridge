import pytest

from paybridge.domain.exceptions import ValidationError
from paybridge.domain.idempotency_policy import normalize_idempotency_key


def test_AC_02_valid_key(): assert normalize_idempotency_key('idem-001') == 'idem-001'

def test_AC_02_bad_characters():
    with pytest.raises(ValidationError): normalize_idempotency_key('idem 001')

def test_AC_02_short_key():
    with pytest.raises(ValidationError): normalize_idempotency_key('x')
