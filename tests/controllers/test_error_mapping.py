from fastapi.testclient import TestClient

from paybridge.main import app


def test_NFR_04_invalid_bearer_format_returns_401():
    with TestClient(app) as c: assert c.get('/api/v1/ops/summary',headers={'Authorization':'Basic x'}).status_code==401
