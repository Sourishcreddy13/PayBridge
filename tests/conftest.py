import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The module-level ``app`` is built at import time; keep its state out of the working directory.
_BOOT = Path(tempfile.mkdtemp(prefix="paybridge-tests-"))
os.environ.setdefault("PAYBRIDGE_DATABASE_PATH", str(_BOOT / "boot.db"))
os.environ.setdefault("PAYBRIDGE_SETTLEMENT_DIR", str(_BOOT / "settlements"))

from paybridge.infrastructure.settings import Settings
from paybridge.main import create_app

CUSTOMER = {"Authorization": "Bearer customer-demo-token"}
OPS = {"Authorization": "Bearer ops-demo-token"}


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        settlement_dir=tmp_path / "settlements",
        refund_auto_approve=False,
        auth_tokens=(
            '{"customer-alice-token": {"subject": "alice", "role": "CUSTOMER"},'
            ' "customer-bob-token": {"subject": "bob", "role": "CUSTOMER"},'
            ' "ops-olivia-token": {"subject": "olivia", "role": "OPS"}}'
        ),
    )


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
