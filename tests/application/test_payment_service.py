from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from paybridge.application.dto import BeneficiaryInput, CreatePaymentInput
from paybridge.domain.enums import BeneficiaryType
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLiteAuditRepository, SQLitePaymentRepository, SQLiteRoutingRepository
from paybridge.application.audit import AuditService
from paybridge.application.retry import RetryPolicy
from paybridge.application.routing_service import RoutingService
from paybridge.application.payment_service import PaymentService
from paybridge.application.rail_service import RailService
from paybridge.infrastructure.rail_adapters import RailScript, StubRailAdapter
from paybridge.infrastructure.rail_attempt_repository import SQLiteRailAttemptRepository
from paybridge.domain.enums import Rail, RailOutcome


def service(tmp_path):
    db=Database(tmp_path/'db.sqlite'); repo=SQLitePaymentRepository(db); rr=SQLiteRoutingRepository(db); ar=AuditService(SQLiteAuditRepository(db)); attempts=SQLiteRailAttemptRepository(db)
    adapters={r.value: StubRailAdapter(r,RailScript((RailOutcome.SUCCESS,)),attempts) for r in Rail}; rails=RailService(repo,adapters)
    class AppRails(RailService):
        def _resolve_route(self,payment_id): return rr.get_route(payment_id).value
    return PaymentService(repo,rr,RoutingService(),AppRails(repo,adapters),ar,RetryPolicy())


def cmd(key='service-idem-01'):
    return CreatePaymentInput(beneficiary=BeneficiaryInput(name='Demo',account_number='123456789012',ifsc='ABCD0123456',beneficiary_type=BeneficiaryType.RETAIL),amount=Decimal('100'),narration='demo',idempotency_key=key)


def test_AC_01_create_returns_pending(tmp_path):
    s=service(tmp_path); v=s.create_payment(cmd(), 'customer','corr'); assert v.state.value=='PENDING' and v.payment_id


def test_AC_02_duplicate_returns_same_id(tmp_path):
    s=service(tmp_path); a=s.create_payment(cmd(), 'customer','corr'); b=s.create_payment(cmd(), 'customer','corr'); assert a.payment_id==b.payment_id
