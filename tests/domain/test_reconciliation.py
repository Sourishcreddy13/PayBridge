from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
from paybridge.domain.enums import BeneficiaryType, PaymentState, ReconciliationStatus
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry
from paybridge.domain.reconciliation_rules import classify_entry


def payment(): return Payment(uuid4(), Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'), Decimal('10'), 'n', 'idem-001', 'INR', datetime.now(timezone.utc), 'actor')

def test_AC_06_match():
    p = payment(); e = SettlementEntry('ext', p.payment_id, p.amount, 'INR', date.today(), ReconciliationStatus.UNMATCHED)
    assert classify_entry(p,e) == 'MATCHED'

def test_AC_06_unmatched_amount():
    p = payment(); e = SettlementEntry('ext', p.payment_id, Decimal('11'), 'INR', date.today(), ReconciliationStatus.UNMATCHED)
    assert classify_entry(p,e) == 'UNMATCHED'
