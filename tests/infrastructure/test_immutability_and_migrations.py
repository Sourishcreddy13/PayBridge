import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from paybridge.domain.enums import ReconciliationStatus
from paybridge.domain.models import SettlementEntry
from paybridge.infrastructure.db import Database, apply_migrations
from tests.helpers import build_stack, command


def mutate(s, sql, *params):
    conn = s.db.connection()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(sql, params)
    finally:
        conn.close()


def test_AC_09_audit_events_cannot_be_updated_or_deleted(tmp_path):
    s = build_stack(tmp_path)
    s.payment_service.create_payment(command("imm-key-0001"), "alice", "c")
    mutate(s, "UPDATE audit_events SET actor='mallory'")
    mutate(s, "DELETE FROM audit_events")


def test_AC_03_routing_decisions_are_immutable(tmp_path):
    s = build_stack(tmp_path)
    s.payment_service.create_payment(command("imm-key-0002"), "alice", "c")
    mutate(s, "UPDATE routing_decisions SET rail='RTGS'")
    mutate(s, "DELETE FROM routing_decisions")


def test_AC_07_settlement_file_registry_is_immutable(tmp_path):
    s = build_stack(tmp_path)
    s.settlements_repo.append_file_record(date(2026, 10, 4), "/x/settlement.csv", "abc")
    mutate(s, "UPDATE settlement_files SET checksum='forged'")
    mutate(s, "DELETE FROM settlement_files")


def test_AC_08_reverse_payments_and_imports_are_immutable(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("imm-key-0003"), "alice", "c")
    s.payment_service.process_payment(p.payment_id, "ops", "c")
    r = s.refund_service.request_refund(p.payment_id, None, "alice", "c", "alice")
    s.refund_service.approve_refund(r.refund_id, "ops", "c")
    mutate(s, "UPDATE reverse_payments SET amount='1.00'")
    mutate(s, "DELETE FROM refund_resolutions")
    mutate(s, "UPDATE refunds SET amount='1.00'")


def test_NFR_05_migrations_are_applied_once_and_recorded(tmp_path):
    db_path = tmp_path / "m.db"
    first = apply_migrations(db_path)
    assert first == ["001_initial", "002_integrity"]
    assert apply_migrations(db_path) == []
    conn = sqlite3.connect(db_path)
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    conn.close()
    assert versions == ["001_initial", "002_integrity"]


def test_NFR_05_failed_migration_rolls_back(tmp_path):
    bad_dir = tmp_path / "migs"
    bad_dir.mkdir()
    (bad_dir / "001_bad.sql").write_text("CREATE TABLE ok_table(x);\nCREATE TABLE ok_table(y);\n")
    with pytest.raises(sqlite3.OperationalError):
        apply_migrations(tmp_path / "bad.db", bad_dir)
    conn = sqlite3.connect(tmp_path / "bad.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ok_table" not in tables


def test_NFR_05_connections_do_not_create_schema(tmp_path):
    from paybridge.infrastructure.db import connect

    conn = connect(tmp_path / "raw.db")
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    conn.close()


def test_database_transaction_commits_and_rolls_back(tmp_path):
    db = Database(tmp_path / "t.db")
    with db.transaction() as conn:
        conn.execute("INSERT INTO idempotency_keys VALUES('k1','p1','now')")
    with pytest.raises(RuntimeError), db.transaction() as conn:
        conn.execute("INSERT INTO idempotency_keys VALUES('k2','p2','now')")
        raise RuntimeError("abort")
    conn = db.connection()
    keys = [r[0] for r in conn.execute("SELECT idempotency_key FROM idempotency_keys")]
    conn.close()
    assert keys == ["k1"]


def test_AC_06_reconciliation_results_are_deduplicated_and_latest_wins(tmp_path):
    s = build_stack(tmp_path)
    day = date(2026, 10, 4)
    unmatched = SettlementEntry("ext-9", None, Decimal("5.00"), "INR", day, ReconciliationStatus.UNMATCHED)
    assert s.settlements_repo.append_reconciliation_result(unmatched) is True
    assert s.settlements_repo.append_reconciliation_result(unmatched) is False
    matched = SettlementEntry("ext-9", None, Decimal("5.00"), "INR", day, ReconciliationStatus.MATCHED)
    assert s.settlements_repo.append_reconciliation_result(matched) is True
    latest = s.settlements_repo.list_reconciliation_results(day)
    assert [e.status for e in latest] == [ReconciliationStatus.MATCHED]
    assert len(s.rows("SELECT 1 FROM reconciliation_results")) == 2  # history retained
