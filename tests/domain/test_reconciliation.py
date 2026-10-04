from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from paybridge.domain.enums import BeneficiaryType, ReconciliationStatus
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry
from paybridge.domain.reconciliation_rules import classify_entry


def payment() -> Payment:
    return Payment(
        uuid4(),
        Beneficiary("123456789012", "ABCD0123456", BeneficiaryType.RETAIL, "Demo"),
        Decimal(10),
        "n",
        "idem-001",
        "INR",
        datetime.now(tz=UTC),
        "actor",
    )


def test_AC_06_match():
    p = payment()
    e = SettlementEntry(
        "ext",
        p.payment_id,
        p.amount,
        "INR",
        datetime.now(tz=UTC).date(),
        ReconciliationStatus.UNMATCHED,
    )
    assert classify_entry(p, e) == "MATCHED"


def test_AC_06_unmatched_amount():
    p = payment()
    e = SettlementEntry(
        "ext",
        p.payment_id,
        Decimal(11),
        "INR",
        datetime.now(tz=UTC).date(),
        ReconciliationStatus.UNMATCHED,
    )
    assert classify_entry(p, e) == "UNMATCHED"
