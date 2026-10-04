from pathlib import Path


def test_domain_has_no_framework_imports():
    for path in Path('src/paybridge/domain').glob('*.py'):
        text=path.read_text()
        assert 'fastapi' not in text.lower()
        assert 'sqlite3' not in text.lower()


def test_controller_does_not_define_routing_rules():
    for path in Path('src/paybridge/controllers').glob('*.py'):
        text=path.read_text()
        assert 'RTGS_MINIMUM' not in text
        assert 'UPI_RETAIL_MAXIMUM' not in text


def test_architecture_directories_exist():
    assert Path('src/paybridge/domain').exists()
    assert Path('src/paybridge/application').exists()
    assert Path('src/paybridge/infrastructure').exists()
    assert Path('src/paybridge/controllers').exists()
