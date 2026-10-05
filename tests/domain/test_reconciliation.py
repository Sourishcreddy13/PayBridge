from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from paybridge.domain.enums import BeneficiaryType, ReconciliationStatus
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry
from paybridge.domain.reconciliation_rules import classify_entry, reconcile_entries


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


DAY = date(2026, 10, 4)


def entry(ref, pid=None, amount=Decimal(10)):
    return SettlementEntry(ref, pid, amount, "INR", DAY, ReconciliationStatus.UNMATCHED)


def test_AC_06_external_reference_matches_even_without_payment_id():
    p = payment()
    [result] = reconcile_entries([entry("RAIL-1")], {p.payment_id: p}, {"RAIL-1": p.payment_id})
    assert result.status is ReconciliationStatus.MATCHED and result.payment_id == p.payment_id


def test_AC_06_reference_with_wrong_amount_is_unmatched():
    p = payment()
    [result] = reconcile_entries([entry("RAIL-1", amount=Decimal(11))], {p.payment_id: p}, {"RAIL-1": p.payment_id})
    assert result.status is ReconciliationStatus.UNMATCHED


def test_AC_06_matching_is_one_to_one():
    p = payment()
    first, second = reconcile_entries(
        [entry("A", p.payment_id), entry("B", p.payment_id)], {p.payment_id: p}, {}
    )
    assert first.status is ReconciliationStatus.MATCHED
    assert second.status is ReconciliationStatus.UNMATCHED


def test_AC_06_payment_id_fallback_when_reference_unknown():
    p = payment()
    [result] = reconcile_entries([entry("UNKNOWN", p.payment_id)], {p.payment_id: p}, {})
    assert result.status is ReconciliationStatus.MATCHED


def test_AC_06_amount_fallback_only_when_unique():
    p, q = payment(), payment()
    [unique] = reconcile_entries([entry("X")], {p.payment_id: p}, {})
    assert unique.status is ReconciliationStatus.MATCHED
    ambiguous = reconcile_entries([entry("X")], {p.payment_id: p, q.payment_id: q}, {})
    assert ambiguous[0].status is ReconciliationStatus.UNMATCHED
    two_lines = reconcile_entries([entry("X"), entry("Y")], {p.payment_id: p}, {})
    assert [r.status for r in two_lines] == [ReconciliationStatus.UNMATCHED] * 2


def test_AC_06_entry_naming_another_payment_never_matches_by_amount():
    p, other = payment(), payment()
    [result] = reconcile_entries([entry("X", other.payment_id)], {p.payment_id: p}, {})
    assert result.status is ReconciliationStatus.UNMATCHED
