import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from paybridge.application.settlement_service import SettlementService
from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus
from paybridge.domain.exceptions import SettlementAlreadyExists
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry
from tests.helpers import build_stack, command


class Payments:
    def __init__(self, payments: list[Payment]) -> None:
        self.payments = payments

    def list_settled(self, business_date: date) -> list[Payment]:
        return self.payments

    def get_current_state(self, payment_id: UUID) -> PaymentState:
        return PaymentState.SETTLED


class Routes:
    def get_route(self, payment_id: UUID) -> Rail:
        return Rail.UPI


class Settlements:
    def __init__(self) -> None:
        self.exists = False
        self.files: list[tuple[date, str, str]] = []

    def settlement_exists(self, business_date: date) -> bool:
        return self.exists

    def list_reconciliation_results(self, business_date: date) -> list[SettlementEntry]:
        return [
            SettlementEntry(
                "ext",
                None,
                Decimal(10),
                "INR",
                business_date,
                ReconciliationStatus.UNMATCHED,
            )
        ]

    def append_file_record(self, business_date: date, path: str, checksum: str) -> None:
        self.files.append((business_date, path, checksum))


def make_payment(day: date) -> Payment:
    return Payment(
        uuid4(),
        Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo User"),
        Decimal("10.00"),
        "demo",
        "settle-test-1",
        "INR",
        datetime.combine(day, datetime.min.time(), UTC),
        "actor",
    )


def test_AC_07_generates_immutable_file(tmp_path):
    day = date(2026, 10, 4)
    repo = Settlements()
    service = SettlementService(Payments([make_payment(day)]), Routes(), repo, tmp_path)
    target = service.generate(day)
    text = target.read_text(encoding="utf-8")
    assert "MATCHED" in text or "UNMATCHED" in text
    assert repo.files


def test_AC_07_existing_file_conflicts(tmp_path):
    day = date(2026, 10, 4)
    target = tmp_path / "settlement-2026-10-04.csv"
    target.write_text("existing", encoding="utf-8")
    repo = Settlements()
    service = SettlementService(Payments([make_payment(day)]), Routes(), repo, tmp_path)
    with pytest.raises(SettlementAlreadyExists):
        service.generate(day)



def settled_payment(s):
    p = s.payment_service.create_payment(command("settle-key-0001"), "alice", "c")
    s.payment_service.process_payment(p.payment_id, "ops", "c")
    return p.payment_id


def today():
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).date()


def test_AC_07_refunded_payment_stays_in_that_days_settlement(tmp_path):
    s = build_stack(tmp_path)
    pid = settled_payment(s)
    r = s.refund_service.request_refund(pid, None, "alice", "c", "alice")
    s.refund_service.approve_refund(r.refund_id, "ops", "c")
    target = s.settlement.generate(today())
    assert str(pid) in target.read_text()


def test_AC_07_concurrent_generation_has_one_winner_and_clean_conflicts(tmp_path):
    s = build_stack(tmp_path)
    settled_payment(s)
    barrier = threading.Barrier(5)

    def go(_):
        barrier.wait()
        try:
            return s.settlement.generate(today())
        except SettlementAlreadyExists as exc:
            return exc

    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(go, range(5)))
    assert len([r for r in results if not isinstance(r, Exception)]) == 1
    assert len(s.rows("SELECT 1 FROM settlement_files")) == 1
    assert [p.name for p in (tmp_path / "settlements").iterdir()] == [f"settlement-{today().isoformat()}.csv"]


def test_AC_07_registry_failure_withdraws_the_published_file(tmp_path, monkeypatch):
    s = build_stack(tmp_path)
    settled_payment(s)

    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(s.settlements_repo, "append_file_record", boom)
    with pytest.raises(RuntimeError):
        s.settlement.generate(today())
    assert list((tmp_path / "settlements").iterdir()) == []
    monkeypatch.undo()
    assert s.settlement.generate(today()).exists()  # no orphan blocks the retry


def test_AC_07_orphan_file_with_matching_content_is_adopted(tmp_path, monkeypatch):
    s = build_stack(tmp_path)
    settled_payment(s)
    original = s.settlements_repo.append_file_record
    monkeypatch.setattr(s.settlements_repo, "append_file_record", lambda *a: (_ for _ in ()).throw(RuntimeError("crash")))
    # Simulate a crash after publication: file stays, nothing registered.
    monkeypatch.setattr("paybridge.application.settlement_service.Path.unlink", lambda *a, **k: None, raising=False)
    with pytest.raises(RuntimeError):
        s.settlement.generate(today())
    monkeypatch.undo()
    assert s.settlements_repo.settlement_exists(today()) is False
    s.settlements_repo.append_file_record = original  # type: ignore[method-assign]
    target = s.settlement.generate(today())
    assert target.exists() and s.settlements_repo.settlement_exists(today())
