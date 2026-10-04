from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from paybridge.application.settlement_service import SettlementService
from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus
from paybridge.domain.exceptions import SettlementAlreadyExists
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry


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
