from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

from paybridge.infrastructure.db import Database
from paybridge.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    # The application uses module-level services; tests patch the database path before creating schema.
    from paybridge import main
    db = Database(tmp_path / 'test.db')
    monkeypatch.setattr(main, 'database', db)
    monkeypatch.setattr(main, 'payment_repo', main.SQLitePaymentRepository(db))
    monkeypatch.setattr(main, 'routing_repo', main.SQLiteRoutingRepository(db))
    monkeypatch.setattr(main, 'audit_repo', main.SQLiteAuditRepository(db))
    monkeypatch.setattr(main, 'settlement_repo', main.SQLiteSettlementRepository(db))
    monkeypatch.setattr(main, 'refund_repo', main.SQLiteRefundRepository(db))
    with TestClient(app) as test_client:
        yield test_client
