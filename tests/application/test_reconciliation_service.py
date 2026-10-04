from datetime import UTC, datetime

from paybridge.application.reconciliation_service import ReconciliationService
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLitePaymentRepository,
    SQLiteSettlementRepository,
)


def test_AC_06_empty_reconciliation_returns_empty(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    service = ReconciliationService(
        SQLitePaymentRepository(db),
        SQLiteSettlementRepository(db),
        SQLiteAuditRepository(db),
    )
    assert service.reconcile(datetime.now(tz=UTC).date(), "ops", "corr") == []
