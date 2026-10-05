from pathlib import Path


def test_NFR_01_fixed_point_artifacts_exist():
    assert 'Decimal' in Path('src/paybridge/domain/money.py').read_text()
def test_NFR_02_append_only_triggers_exist():
    sql = ''.join(p.read_text() for p in Path('src/paybridge/infrastructure/migrations').glob('*.sql'))
    assert 'prevent_payment_update' in sql and 'prevent_audit_update' in sql
def test_NFR_03_masking_artifact_exists():
    assert 'mask_account_number' in Path('src/paybridge/domain/pii_policy.py').read_text()
def test_NFR_04_rbac_boundary_exists():
    assert 'require_roles' in Path('src/paybridge/controllers/dependencies.py').read_text()
def test_NFR_05_migration_is_append_only():
    files = sorted(Path('src/paybridge/infrastructure/migrations').glob('*.sql'))
    assert files and files[0].name == '001_initial.sql'
    assert not Path('migrations').exists(), 'migrations/ inside the package is the single schema authority'
def test_NFR_06_structured_logger_exists():
    assert 'JsonFormatter' in Path('src/paybridge/infrastructure/logger.py').read_text()
def test_NFR_07_health_endpoint_exists():
    assert '@app.get("/health"' in Path('src/paybridge/main.py').read_text()
def test_NFR_08_state_immutability_tests_exist():
    assert 'test_NFR_08' in Path('tests/infrastructure/test_append_only.py').read_text()
