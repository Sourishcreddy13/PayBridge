import json
import logging

import pytest

from paybridge.infrastructure.settings import Settings
from tests.controllers.test_authorization_and_contracts import OPS, create


def test_NFR_04_non_dev_environment_requires_explicit_tokens():
    with pytest.raises(ValueError):
        Settings(environment="production")


def test_NFR_04_non_dev_environment_rejects_demo_and_short_tokens():
    short = json.dumps({"short": {"subject": "u", "role": "OPS"}})
    with pytest.raises(ValueError):
        Settings(environment="production", auth_tokens=short)
    demo = json.dumps({"ops-demo-token": {"subject": "u", "role": "OPS"}})
    with pytest.raises(ValueError):
        Settings(environment="production", auth_tokens=demo)


def test_NFR_04_non_dev_accepts_strong_explicit_tokens():
    tokens = json.dumps({"t" * 32: {"subject": "olivia", "role": "OPS"}})
    s = Settings(environment="production", auth_tokens=tokens)
    assert list(s.token_identities().values()) == [("olivia", "OPS")]


def test_NFR_04_malformed_token_config_is_rejected():
    with pytest.raises(ValueError):
        Settings(auth_tokens="not json")
    with pytest.raises(ValueError):
        Settings(auth_tokens=json.dumps({"tok": {"subject": "u", "role": "ROOT"}}))


def test_NFR_06_lifecycle_events_are_logged_with_ids(client, caplog):
    caplog.set_level(logging.INFO)
    pid = create(client)
    client.post(f"/api/v1/payments/{pid}/process", headers=OPS, params={})
    events = {r.event: r for r in caplog.records if hasattr(r, "event")}
    for name in ("payment_created", "payment_processing", "rail_attempt", "payment_settled"):
        assert name in events, name
        assert events[name].correlation_id and events[name].payment_id == pid
    assert events["payment_created"].actor == "alice"


def test_NFR_06_json_formatter_includes_event_fields():
    from paybridge.infrastructure.logger import JsonFormatter

    record = logging.LogRecord("n", logging.INFO, "f", 1, "msg", None, None)
    record.event = "x"
    record.correlation_id = "c-1"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "x" and payload["correlation_id"] == "c-1" and payload["message"] == "msg"
