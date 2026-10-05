import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from paybridge.domain.enums import PaymentState, RailOutcome
from paybridge.domain.exceptions import InvalidPaymentStateException
from paybridge.domain.models import PaymentTransition, RailResponse, utc_now
from tests.helpers import build_stack, command


def run_parallel(fn, n=6):
    barrier = threading.Barrier(n)

    def task(_):
        barrier.wait()
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - outcomes are asserted by the caller
            return exc

    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(task, range(n)))


def test_NFR_08_concurrent_process_submits_to_rail_once(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("conc-key-001"), "alice", "c")
    results = run_parallel(lambda: s.payment_service.process_payment(p.payment_id, "ops", "c"))
    ok = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(ok) == 1
    assert all(isinstance(e, InvalidPaymentStateException) for e in errors)
    assert len(s.attempts.list_attempts(p.payment_id)) == 1
    states = [r["to_state"] for r in s.rows("SELECT to_state FROM payment_transitions ORDER BY id")]
    assert states == ["PROCESSING", "SETTLED"]


def test_NFR_08_concurrent_refund_approvals_complete_once(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("conc-key-002"), "alice", "c")
    s.payment_service.process_payment(p.payment_id, "ops", "c")
    refund = s.refund_service.request_refund(p.payment_id, None, "alice", "c", "alice")
    results = run_parallel(lambda: s.refund_service.approve_refund(refund.refund_id, "ops", "c"))
    assert len([r for r in results if not isinstance(r, Exception)]) == 1
    assert len(s.rows("SELECT 1 FROM reverse_payments")) == 1
    assert [r["to_state"] for r in s.rows("SELECT to_state FROM payment_transitions WHERE to_state='REFUNDED'")] == ["REFUNDED"]


def test_NFR_08_concurrent_refund_requests_create_one_refund(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("conc-key-003"), "alice", "c")
    s.payment_service.process_payment(p.payment_id, "ops", "c")
    results = run_parallel(lambda: s.refund_service.request_refund(p.payment_id, None, "alice", "c", "alice"))
    assert len([r for r in results if not isinstance(r, Exception)]) == 1
    assert len(s.rows("SELECT 1 FROM refunds")) == 1


def test_NFR_08_repository_rejects_stale_and_illegal_transitions(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("conc-key-004"), "alice", "c")
    pid = p.payment_id
    with pytest.raises(InvalidPaymentStateException):  # legal edge, but stale from_state
        s.payments.append_transition(PaymentTransition(pid, PaymentState.PROCESSING, PaymentState.SETTLED, utc_now(), "x"))
    with pytest.raises(InvalidPaymentStateException):  # illegal edge from the real state
        s.payments.append_transition(PaymentTransition(pid, PaymentState.PENDING, PaymentState.REFUNDED, utc_now(), "x"))
    assert s.payments.list_transitions(pid) == []


def test_NFR_08_database_trigger_blocks_lifecycle_bypass(tmp_path):
    import sqlite3

    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("conc-key-005"), "alice", "c")
    conn = s.db.connection()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute(
                "INSERT INTO payment_transitions(payment_id,from_state,to_state,at,actor) VALUES(?,?,?,?,?)",
                (str(p.payment_id), "PENDING", "REFUNDED", "2026-10-04T00:00:00+00:00", "x"),
            )
    finally:
        conn.close()


def test_AC_09_create_is_atomic_with_routing_and_audit(tmp_path):
    s = build_stack(tmp_path)
    s.payment_service.create_payment(command("atomic-key-1"), "alice", "corr-1")
    events = [r["event_type"] for r in s.rows("SELECT event_type FROM audit_events ORDER BY id")]
    assert events == ["PAYMENT_CREATED", "ROUTING_DECISION"]
    assert len(s.rows("SELECT 1 FROM routing_decisions")) == 1


def test_AC_09_failed_routing_persistence_rolls_back_payment(tmp_path, monkeypatch):
    import paybridge.infrastructure.repositories as repos

    s = build_stack(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("routing store unavailable")

    monkeypatch.setattr(repos, "_insert_routing", boom)
    with pytest.raises(RuntimeError):
        s.payment_service.create_payment(command("atomic-key-2"), "alice", "c")
    assert s.rows("SELECT 1 FROM payments") == [] and s.rows("SELECT 1 FROM idempotency_keys") == []
    monkeypatch.undo()
    assert s.payment_service.create_payment(command("atomic-key-2"), "alice", "c").rail is not None


def test_AC_05_adapter_crash_fails_payment_instead_of_stranding_processing(tmp_path):
    class Exploding:
        def submit(self, payment, attempt):
            raise ConnectionError("rail down")

    s = build_stack(tmp_path, adapters_override={"UPI": Exploding()})
    p = s.payment_service.create_payment(command("crash-key-001"), "alice", "c")
    view = s.payment_service.process_payment(p.payment_id, "ops", "c")
    assert view.state is PaymentState.FAILED and view.reason_code == "RAIL_ERROR"


def test_AC_04_failed_payment_exposes_reason_code(tmp_path):
    from paybridge.domain.enums import Rail

    s = build_stack(tmp_path, scripts={Rail.UPI: (RailOutcome.PERMANENT_FAILURE,)})
    p = s.payment_service.create_payment(command("reason-key-001"), "alice", "c")
    view = s.payment_service.process_payment(p.payment_id, "ops", "c")
    assert view.state is PaymentState.FAILED and view.reason_code == "SIMULATED"


def test_AC_09_every_transition_has_audit_evidence(tmp_path):
    s = build_stack(tmp_path)
    p = s.payment_service.create_payment(command("audit-key-001"), "alice", "c")
    s.payment_service.process_payment(p.payment_id, "ops", "c")
    transitions = s.rows("SELECT 1 FROM payment_transitions")
    audited = s.rows("SELECT 1 FROM audit_events WHERE event_type='PAYMENT_TRANSITION'")
    assert len(transitions) == len(audited) == 2


def test_rail_response_dataclass_roundtrip():
    assert RailResponse("SUCCESS", "x", None, 1).attempt == 1
