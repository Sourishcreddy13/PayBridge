from pathlib import Path


def test_domain_has_no_application_dependency():
    text=''.join(p.read_text() for p in Path('src/paybridge/domain').glob('*.py'))
    assert 'paybridge.application' not in text


def test_application_owns_orchestration():
    service_names={p.name for p in Path('src/paybridge/application').glob('*_service.py')}
    assert {'payment_service.py','routing_service.py','reconciliation_service.py','settlement_service.py','refund_service.py'} <= service_names
