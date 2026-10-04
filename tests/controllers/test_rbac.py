from fastapi.testclient import TestClient
from paybridge.main import app


def test_NFR_04_missing_auth_is_rejected():
    with TestClient(app) as c: assert c.get('/api/v1/ops/summary').status_code==401


def test_AC_10_customer_cannot_use_ops_dashboard():
    with TestClient(app) as c: assert c.get('/api/v1/ops/summary',headers={'Authorization':'Bearer customer-demo-token'}).status_code==403
