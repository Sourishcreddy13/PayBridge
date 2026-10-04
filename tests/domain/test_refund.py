from decimal import Decimal
import pytest
from paybridge.domain.enums import PaymentState
from paybridge.domain.exceptions import RefundNotAllowed, ValidationError
from paybridge.domain.refund_policy import validate_refund


def test_AC_08_settled_full_refund(): validate_refund(PaymentState.SETTLED, Decimal('20.00'), Decimal('20.00'))

def test_AC_08_nonsettled_rejected():
    with pytest.raises(RefundNotAllowed): validate_refund(PaymentState.PROCESSING, Decimal('20.00'), Decimal('20.00'))

def test_AC_08_over_refund_rejected():
    with pytest.raises(ValidationError): validate_refund(PaymentState.SETTLED, Decimal('20.00'), Decimal('20.01'))
