from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.models import Beneficiary, Payment
from paybridge.domain.exceptions import ValidationError

def test_AC_01_payment_is_immutable():
    p=Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'),Decimal('1'),'demo','models-idem-1','INR',datetime.now(timezone.utc),'actor')
    with pytest.raises(Exception): p.amount=Decimal('2')

def test_AC_01_bad_currency():
    with pytest.raises(ValidationError): Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'),Decimal('1'),'demo','models-idem-2','USD',datetime.now(timezone.utc),'actor')
