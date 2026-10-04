from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from paybridge.application.operational_queue_service import OperationalQueueService
from paybridge.domain.enums import BeneficiaryType, PaymentState, ReconciliationStatus, Rail
from paybridge.domain.models import Beneficiary, Payment, PaymentTransition, SettlementEntry


class Payments:
    def __init__(self, payments, state): self._payments, self._state = payments, state
    def list_payments(self): return self._payments
    def get_current_state(self, payment_id): return self._state
    def get_payment(self, payment_id): return self._payments[0]


class Settlements:
    def __init__(self, entries): self.entries=entries
    def list_reconciliation_results(self, business_date): return self.entries


class Refunds:
    def list_refunds(self): return []


class Routes:
    def get_route(self, payment_id): return Rail.NEFT


def payment(state_day=True):
    return Payment(uuid4(), Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'), Decimal('10'), 'demo', 'ops-idem-1', 'INR', datetime.now(timezone.utc), 'actor')


def test_AC_10_unmatched_queue():
    entry=SettlementEntry('ext',None,Decimal('10'),'INR',datetime.now(timezone.utc).date(),ReconciliationStatus.UNMATCHED)
    service=OperationalQueueService(Payments([],PaymentState.PENDING),Settlements([entry]),Refunds(),Routes())
    assert service.unmatched(entry.business_date) == [entry]


def test_AC_10_retry_candidates():
    item=payment(); service=OperationalQueueService(Payments([item],PaymentState.PROCESSING),Settlements([]),Refunds(),Routes())
    assert service.retry_candidates(item.created_at.date()) == [item]


def test_AC_10_rail_breakdown():
    item=payment(); service=OperationalQueueService(Payments([item],PaymentState.PENDING),Settlements([]),Refunds(),Routes())
    assert service.rail_breakdown(item.created_at.date()) == {'NEFT': 1}


def test_AC_10_payment_state_requires_existing_payment():
    item=payment(); service=OperationalQueueService(Payments([item],PaymentState.PROCESSING),Settlements([]),Refunds(),Routes()); assert service.payment_state(item.payment_id) is PaymentState.PROCESSING

def test_AC_10_empty_rail_breakdown_is_empty():
    service=OperationalQueueService(Payments([],PaymentState.PENDING),Settlements([]),Refunds(),Routes()); assert service.rail_breakdown(datetime.now(timezone.utc).date()) == {}
