from decimal import Decimal

from paybridge.application.audit import AuditService
from paybridge.application.dto import BeneficiaryInput, CreatePaymentInput
from paybridge.application.payment_service import PaymentService
from paybridge.application.rail_service import RailService
from paybridge.application.retry import RetryPolicy
from paybridge.application.routing_service import RoutingService
from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, RailOutcome
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.rail_adapters import RailScript, StubRailAdapter
from paybridge.infrastructure.rail_attempt_repository import SQLiteRailAttemptRepository
from paybridge.infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLitePaymentRepository,
    SQLiteRoutingRepository,
)


class LocalRailService(RailService):
    def __init__(self, repo, adapters, routes):
        super().__init__(repo, adapters); self.routes=routes
    def _resolve_route(self, payment_id):
        route=self.routes.get_route(payment_id)
        if route is None: raise RuntimeError('missing route')
        return route.value


def build(tmp_path, outcome_scripts=None):
    db=Database(tmp_path/'flow.db'); payments=SQLitePaymentRepository(db); routes=SQLiteRoutingRepository(db); audit=AuditService(SQLiteAuditRepository(db)); attempts=SQLiteRailAttemptRepository(db)
    scripts=outcome_scripts or {rail: (RailOutcome.SUCCESS,) for rail in Rail}
    adapters={rail.value: StubRailAdapter(rail,RailScript(tuple(scripts[rail])),attempts) for rail in Rail}
    rail_service=LocalRailService(payments,adapters,routes)
    return PaymentService(payments,routes,RoutingService(),rail_service,audit,RetryPolicy(3,Decimal(0)))


def command(key='flow-idem-01',amount='100.00'):
    return CreatePaymentInput(beneficiary=BeneficiaryInput(name='Demo User',account_number='123456789012',ifsc='ABCD0123456',beneficiary_type=BeneficiaryType.RETAIL),amount=Decimal(amount),narration='synthetic flow',idempotency_key=key)


def test_AC_01_AC_03_create_persists_route(tmp_path):
    service=build(tmp_path); view=service.create_payment(command(), 'customer','corr'); assert view.state is PaymentState.PENDING and view.rail is Rail.UPI


def test_AC_02_replay_has_one_identity(tmp_path):
    service=build(tmp_path); first=service.create_payment(command(), 'customer','corr'); replay=service.create_payment(command(), 'customer','corr'); assert first.payment_id==replay.payment_id


def test_AC_04_process_reaches_settled(tmp_path):
    service=build(tmp_path); created=service.create_payment(command(), 'customer','corr'); settled=service.process_payment(created.payment_id,'customer','corr'); assert settled.state is PaymentState.SETTLED


def test_AC_05_transient_script_retries_and_settles(tmp_path):
    scripts={rail: (RailOutcome.SUCCESS,) for rail in Rail}; scripts[Rail.UPI]=(RailOutcome.TRANSIENT_FAILURE,RailOutcome.SUCCESS); service=build(tmp_path,scripts); created=service.create_payment(command(), 'customer','corr'); settled=service.process_payment(created.payment_id,'customer','corr'); assert settled.state is PaymentState.SETTLED


def test_AC_05_permanent_script_fails(tmp_path):
    scripts={rail: (RailOutcome.SUCCESS,) for rail in Rail}; scripts[Rail.UPI]=(RailOutcome.PERMANENT_FAILURE,); service=build(tmp_path,scripts); created=service.create_payment(command(), 'customer','corr'); failed=service.process_payment(created.payment_id,'customer','corr'); assert failed.state is PaymentState.FAILED


def test_AC_09_audit_is_created_for_route_and_states(tmp_path):
    service=build(tmp_path); created=service.create_payment(command(), 'customer','corr'); service.process_payment(created.payment_id,'customer','corr')
    db=service._repository._db.connection()
    try:
        rows=db.execute('SELECT event_type FROM audit_events ORDER BY id').fetchall(); assert any(r['event_type']=='ROUTING_DECISION' for r in rows); assert any(r['event_type']=='PAYMENT_TRANSITION' for r in rows)
    finally: db.close()
