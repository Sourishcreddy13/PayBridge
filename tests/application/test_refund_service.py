from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from paybridge.domain.enums import BeneficiaryType, PaymentState, Role
from paybridge.domain.models import Beneficiary, Payment, PaymentTransition
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLiteAuditRepository, SQLitePaymentRepository, SQLiteRefundRepository
from paybridge.application.audit import AuditService
from paybridge.application.refund_service import RefundService


def test_AC_08_refund_creates_reverse_entry(tmp_path):
    db=Database(tmp_path/'db.sqlite'); pr=SQLitePaymentRepository(db); pid=uuid4(); p=Payment(pid,Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'),Decimal('50'),'demo','refund-test-1','INR',datetime.now(timezone.utc),'customer'); pr.reserve_and_append_payment(p); pr.append_transition(PaymentTransition(pid,PaymentState.PENDING,PaymentState.PROCESSING,datetime.now(timezone.utc),'customer')); pr.append_transition(PaymentTransition(pid,PaymentState.PROCESSING,PaymentState.SETTLED,datetime.now(timezone.utc),'customer')); rs=RefundService(pr,SQLiteRefundRepository(db),AuditService(SQLiteAuditRepository(db))); refund=rs.request_refund(pid,Decimal('50'),'customer','corr'); assert refund.original_payment_id==pid; assert pr.get_current_state(pid) is PaymentState.REFUNDED
