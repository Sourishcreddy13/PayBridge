from datetime import date
from decimal import Decimal
from uuid import uuid4
from paybridge.application.reconciliation_service import ReconciliationService
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLiteAuditRepository, SQLitePaymentRepository, SQLiteSettlementRepository

def test_AC_06_empty_reconciliation_returns_empty(tmp_path):
    db=Database(tmp_path/'db.sqlite'); s=ReconciliationService(SQLitePaymentRepository(db),SQLiteSettlementRepository(db),SQLiteAuditRepository(db)); assert s.reconcile(date.today(),'ops','corr')==[]
