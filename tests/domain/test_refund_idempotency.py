from decimal import Decimal
from uuid import uuid4
import pytest
from paybridge.domain.refund_idempotency import refund_reference, validate_refund_reference

def test_refund_reference_is_deterministic():
    pid=uuid4(); ref=refund_reference(pid,Decimal('12.30')); assert ref.startswith('RF-') and '12.30' in ref

def test_refund_reference_validates():
    assert validate_refund_reference('RF-123456789012-10.00').startswith('RF-')

def test_refund_reference_rejects_invalid_value():
    with pytest.raises(Exception): validate_refund_reference('bad-reference')
