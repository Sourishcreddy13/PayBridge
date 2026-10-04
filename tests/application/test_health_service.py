from paybridge.application.health_service import HealthService

def test_NFR_07_health_check_is_fast():
    service=HealthService(lambda: None); status, elapsed=service.check(); assert status=='UP' and elapsed < 1.0
