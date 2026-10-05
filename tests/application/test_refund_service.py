from decimal import Decimal
from uuid import uuid4

import pytest

from paybridge.domain.enums import PaymentState, RefundStatus
from paybridge.domain.exceptions import PaymentNotFound, RefundNotAllowed, ValidationError
from tests.helpers import build_stack, command


def settled(s, key="refund-key-001", owner="alice"):
    p = s.payment_service.create_payment(command(key, amount="100.00"), owner, "c1")
    s.payment_service.process_payment(p.payment_id, "ops", "c2")
    return p.payment_id


def test_AC_08_refund_request_then_approval_creates_reverse_entry(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    requested = s.refund_service.request_refund(pid, Decimal("100.00"), "alice", "c3", "alice")
    assert requested.status is RefundStatus.PENDING
    assert s.payments.get_current_state(pid) is PaymentState.SETTLED  # nothing moves until approval
    done = s.refund_service.approve_refund(requested.refund_id, "ops", "c4")
    assert done.status is RefundStatus.COMPLETED
    assert s.payments.get_current_state(pid) is PaymentState.REFUNDED
    reverse = s.rows("SELECT * FROM reverse_payments")
    assert len(reverse) == 1
    assert reverse[0]["reverse_payment_id"] == str(done.reverse_payment_id)
    assert reverse[0]["original_payment_id"] == str(pid) and reverse[0]["amount"] == "100.00"


def test_AC_08_only_full_refunds_are_supported(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    with pytest.raises(ValidationError):
        s.refund_service.request_refund(pid, Decimal("10.00"), "alice", "c", "alice")


def test_AC_08_duplicate_refund_request_is_rejected(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    s.refund_service.request_refund(pid, None, "alice", "c", "alice")
    with pytest.raises(RefundNotAllowed):
        s.refund_service.request_refund(pid, None, "alice", "c", "alice")


def test_AC_08_unsettled_payment_cannot_be_refunded(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("refund-key-002"), "alice", "c")
    with pytest.raises(RefundNotAllowed):
        s.refund_service.request_refund(p.payment_id, None, "alice", "c", "alice")


def test_AC_08_other_customers_payment_is_not_found(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    with pytest.raises(PaymentNotFound):
        s.refund_service.request_refund(pid, None, "bob", "c", "bob")


def test_AC_08_rejection_is_final_and_blocks_approval(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    r = s.refund_service.request_refund(pid, None, "alice", "c", "alice")
    rejected = s.refund_service.reject_refund(r.refund_id, "policy", "ops", "c")
    assert rejected.status is RefundStatus.FAILED
    with pytest.raises(RefundNotAllowed):
        s.refund_service.approve_refund(r.refund_id, "ops", "c")
    assert s.payments.get_current_state(pid) is PaymentState.SETTLED


def test_AC_08_unknown_refund_is_not_found(tmp_path):
    s = build_stack(tmp_path)
    with pytest.raises(PaymentNotFound):
        s.refund_service.approve_refund(uuid4(), "ops", "c")


def test_AC_09_refund_events_are_audited(tmp_path):
    s = build_stack(tmp_path)
    pid = settled(s)
    r = s.refund_service.request_refund(pid, None, "alice", "c", "alice")
    s.refund_service.approve_refund(r.refund_id, "ops", "c")
    events = {row["event_type"] for row in s.rows("SELECT event_type FROM audit_events")}
    assert {"REFUND_REQUESTED", "REFUND_COMPLETED"} <= events


def test_AC_08_default_policy_completes_refund_immediately(tmp_path):
    """AC-08 as specified: a refund request yields the reverse entry and REFUNDED at once."""
    s = build_stack(tmp_path, auto_refund=True)
    pid = settled(s)
    view = s.refund_service.request_refund(pid, None, "alice", "c", "alice")
    assert view.status is RefundStatus.COMPLETED
    assert s.payments.get_current_state(pid) is PaymentState.REFUNDED
    assert len(s.rows("SELECT 1 FROM reverse_payments")) == 1
    actors = {r["actor"] for r in s.rows("SELECT actor FROM audit_events WHERE event_type LIKE 'REFUND%'")}
    assert actors == {"alice"}


def test_AC_08_auto_policy_is_still_full_only_and_owner_scoped(tmp_path):
    s = build_stack(tmp_path, auto_refund=True)
    pid = settled(s)
    with pytest.raises(PaymentNotFound):
        s.refund_service.request_refund(pid, None, "bob", "c", "bob")
    with pytest.raises(ValidationError):
        s.refund_service.request_refund(pid, Decimal("1.00"), "alice", "c", "alice")
