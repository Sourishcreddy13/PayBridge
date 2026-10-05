from datetime import UTC, datetime
from uuid import uuid4

PAYMENT = {
    "beneficiary": {"name": "Demo User", "account_number": "123456789012", "ifsc": "ABCD0123456", "beneficiary_type": "RETAIL"},
    "amount": "100.00",
    "narration": "invoice",
    "idempotency_key": "http-key-0001",
}
ALICE = {"Authorization": "Bearer customer-alice-token"}
BOB = {"Authorization": "Bearer customer-bob-token"}
OPS = {"Authorization": "Bearer ops-olivia-token"}


def create(client, key="http-key-0001", headers=ALICE):
    r = client.post("/api/v1/payments", json={**PAYMENT, "idempotency_key": key}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["payment_id"]


def test_NFR_04_customer_cannot_read_another_customers_payment(client):
    pid = create(client)
    assert client.get(f"/api/v1/payments/{pid}", headers=ALICE).status_code == 200
    assert client.get(f"/api/v1/payments/{pid}", headers=BOB).status_code == 404
    assert client.get(f"/api/v1/payments/{pid}/timeline", headers=BOB).status_code == 404
    assert client.get(f"/api/v1/payments/{pid}", headers=OPS).status_code == 200


def test_NFR_04_history_is_scoped_to_the_customer(client):
    create(client, "http-key-0002", ALICE)
    create(client, "http-key-0003", BOB)
    assert len(client.get("/api/v1/payments", headers=ALICE).json()) == 1
    assert len(client.get("/api/v1/payments", headers=OPS).json()) == 2


def test_NFR_04_customer_cannot_execute_rail_submission(client):
    pid = create(client)
    assert client.post(f"/api/v1/payments/{pid}/process", headers=ALICE).status_code == 403
    done = client.post(f"/api/v1/payments/{pid}/process", headers=OPS)
    assert done.status_code == 200 and done.json()["state"] == "SETTLED"


def test_NFR_04_audit_actor_is_the_authenticated_subject(client, settings):
    pid = create(client)
    client.post(f"/api/v1/payments/{pid}/process", headers=OPS)
    import sqlite3

    conn = sqlite3.connect(settings.database_path)
    actors = {row[0] for row in conn.execute("SELECT actor FROM audit_events")}
    conn.close()
    assert actors == {"alice", "olivia"}


def test_AC_04_errors_use_declared_http_semantics(client):
    pid = create(client)
    client.post(f"/api/v1/payments/{pid}/process", headers=OPS)
    again = client.post(f"/api/v1/payments/{pid}/process", headers=OPS)
    assert again.status_code == 409 and "correlation_id" in again.json()
    assert client.post(f"/api/v1/payments/{uuid4()}/process", headers=OPS).status_code == 404


def test_AC_01_invalid_payment_is_a_422_not_a_500(client):
    bad = {**PAYMENT, "beneficiary": {**PAYMENT["beneficiary"], "ifsc": "XXXX0123456"}}
    assert client.post("/api/v1/payments", json=bad, headers=ALICE).status_code == 422


def test_AC_06_invalid_reconciliation_date_is_a_4xx(client):
    assert client.post("/api/v1/reconciliation/not-a-date", headers=OPS).status_code == 422


def test_NFR_06_correlation_id_is_validated_and_bounded(client):
    ok = client.get("/health", headers={"X-Correlation-ID": "abc-123"})
    assert ok.headers["X-Correlation-ID"] == "abc-123"
    for hostile in ("x" * 5000, "bad id with spaces", "new\\nline"):
        r = client.get("/health", headers={"X-Correlation-ID": hostile})
        assert r.headers["X-Correlation-ID"] != hostile and len(r.headers["X-Correlation-ID"]) <= 64


def test_AC_08_refund_workflow_over_http(client):
    pid = create(client)
    client.post(f"/api/v1/payments/{pid}/process", headers=OPS)
    assert client.post(f"/api/v1/payments/{pid}/refund", json={}, headers=BOB).status_code == 404
    partial = client.post(f"/api/v1/payments/{pid}/refund", json={"amount": "10.00"}, headers=ALICE)
    assert partial.status_code == 422
    req = client.post(f"/api/v1/payments/{pid}/refund", json={}, headers=ALICE)
    assert req.status_code == 201 and req.json()["status"] == "PENDING"
    assert client.post(f"/api/v1/payments/{pid}/refund", json={}, headers=ALICE).status_code == 409
    assert client.get(f"/api/v1/payments/{pid}/refund", headers=ALICE).json()["status"] == "PENDING"
    refund_id = req.json()["refund_id"]
    assert client.post(f"/api/v1/refunds/{refund_id}/approve", headers=ALICE).status_code == 403
    done = client.post(f"/api/v1/refunds/{refund_id}/approve", headers=OPS)
    assert done.status_code == 200 and done.json()["status"] == "COMPLETED"
    assert client.get(f"/api/v1/payments/{pid}", headers=ALICE).json()["state"] == "REFUNDED"
    assert client.post(f"/api/v1/refunds/{refund_id}/approve", headers=OPS).status_code == 409


def test_AC_06_settlement_import_reconcile_and_generate_over_http(client):
    pid = create(client)
    done = client.post(f"/api/v1/payments/{pid}/process", headers=OPS).json()
    day = datetime.now(tz=UTC).date().isoformat()
    csv_body = f"external_reference,payment_id,amount,currency\nbank-1,{pid},{done['amount']},INR\nbank-2,,999.00,INR\n"
    first = client.post(f"/api/v1/settlement/import?business_date={day}", content=csv_body, headers=OPS)
    assert first.status_code == 201 and first.json()["entry_count"] == 2
    replay = client.post(f"/api/v1/settlement/import?business_date={day}", content=csv_body, headers=OPS)
    assert replay.status_code == 409
    assert client.post(f"/api/v1/settlement/import?business_date={day}", content=csv_body, headers=ALICE).status_code == 403

    statuses = [r["status"] for r in client.post(f"/api/v1/reconciliation/{day}", headers=OPS).json()]
    assert statuses == ["MATCHED", "UNMATCHED"]
    client.post(f"/api/v1/reconciliation/{day}", headers=OPS)  # re-run is idempotent
    summary = client.get(f"/api/v1/ops/summary?business_date={day}", headers=OPS).json()
    assert len(summary["unmatched_queue"]) == 1
    gen = client.post("/api/v1/settlement", json={"business_date": day}, headers=OPS)
    assert gen.status_code == 200
    assert client.post("/api/v1/settlement", json={"business_date": day}, headers=OPS).status_code == 409


def test_AC_06_malformed_import_is_422(client):
    day = datetime.now(tz=UTC).date().isoformat()
    bad = "external_reference,payment_id,amount,currency\n,,10.00,INR\n"
    assert client.post(f"/api/v1/settlement/import?business_date={day}", content=bad, headers=OPS).status_code == 422


def test_NFR_07_health_reports_database(client):
    assert client.get("/health").json() == {"status": "UP", "database": "UP"}


def test_AC_08_default_app_policy_refunds_immediately(tmp_path):
    from fastapi.testclient import TestClient

    from paybridge.infrastructure.settings import Settings
    from paybridge.main import create_app

    settings = Settings(
        database_path=tmp_path / "auto.db",
        settlement_dir=tmp_path / "s",
        auth_tokens='{"customer-alice-token": {"subject": "alice", "role": "CUSTOMER"}, "ops-olivia-token": {"subject": "olivia", "role": "OPS"}}',
    )
    assert settings.refund_auto_approve is True
    with TestClient(create_app(settings)) as c:
        pid = create(c)
        c.post(f"/api/v1/payments/{pid}/process", headers=OPS)
        r = c.post(f"/api/v1/payments/{pid}/refund", json={}, headers=ALICE)
        assert r.status_code == 201 and r.json()["status"] == "COMPLETED"
        assert c.get(f"/api/v1/payments/{pid}", headers=ALICE).json()["state"] == "REFUNDED"


def test_NFR_04_me_reports_subject_and_role(client):
    assert client.get("/api/v1/me", headers=ALICE).json() == {"subject": "alice", "role": "CUSTOMER"}
    assert client.get("/api/v1/me", headers=OPS).json() == {"subject": "olivia", "role": "OPS"}
    assert client.get("/api/v1/me").status_code == 401
