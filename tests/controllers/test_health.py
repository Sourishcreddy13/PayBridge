from fastapi.testclient import TestClient
from paybridge.main import app

def test_NFR_07_health():
    with TestClient(app) as c:
        response=c.get('/health'); assert response.status_code==200 and response.json()['status']=='UP'
