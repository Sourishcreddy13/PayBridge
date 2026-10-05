from datetime import UTC, datetime

from paybridge.domain.enums import PaymentState, ReconciliationStatus
from paybridge.domain.models import SettlementEntry
from tests.helpers import build_stack, command


def today():
    return datetime.now(tz=UTC).date()


def test_AC_10_summary_counts_rail_and_status(tmp_path):
    s = build_stack(tmp_path)
    a = s.payment_service.create_payment(command("dash-key-001"), "alice", "c1")
    s.payment_service.create_payment(command("dash-key-002", amount="300000.00"), "alice", "c2")
    s.payment_service.process_payment(a.payment_id, "ops", "c3")
    summary = s.dashboard.summary(today())
    assert summary.volumes_by_status["SETTLED"] == 1 and summary.volumes_by_status["PENDING"] == 1
    assert summary.volumes_by_rail == {"UPI": 1, "RTGS": 1}
    assert summary.payments_today == 2
    assert [q.rail.value for q in summary.pending_queue] == ["RTGS"]


def test_AC_10_summary_returns_unmatched_queue(tmp_path):
    s = build_stack(tmp_path)
    entry = SettlementEntry("ext-1", None, __import__("decimal").Decimal("12.00"), "INR", today(), ReconciliationStatus.UNMATCHED)
    s.settlements_repo.append_entries([entry])
    s.reconciliation.reconcile(today(), "ops", "c")
    assert len(s.dashboard.summary(today()).unmatched_queue) == 1


def test_AC_10_summary_returns_refund_queue_and_retry_queue(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("dash-key-003"), "alice", "c1")
    s.payment_service.process_payment(p.payment_id, "ops", "c2")
    s.refund_service.request_refund(p.payment_id, None, "alice", "c3", "alice")
    summary = s.dashboard.summary(today())
    assert [r.status.value for r in summary.refund_queue] == ["PENDING"]
    assert summary.retry_queue == []


def test_AC_10_processing_payments_appear_in_retry_queue(tmp_path):
    from paybridge.domain.models import PaymentTransition, utc_now

    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("dash-key-004"), "alice", "c1")
    s.payments.append_transition(PaymentTransition(p.payment_id, PaymentState.PENDING, PaymentState.PROCESSING, utc_now(), "ops"))
    assert [q.payment_id for q in s.dashboard.summary(today()).retry_queue] == [p.payment_id]
