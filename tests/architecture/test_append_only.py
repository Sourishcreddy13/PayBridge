import re
from pathlib import Path


def test_NFR_02_repositories_have_no_mutating_dml():
    text=''.join(p.read_text().upper() for p in Path('src/paybridge/infrastructure').glob('*.py') if p.name != 'db.py')
    assert not re.search(r"\bUPDATE\b|\bDELETE\b", text)


def test_NFR_02_database_has_immutable_triggers():
    text=''.join(p.read_text() for p in Path('src/paybridge/infrastructure/migrations').glob('*.sql')).upper()
    for table in ('PAYMENTS','PAYMENT_TRANSITIONS','SETTLEMENT_ENTRIES','REFUNDS','RECONCILIATION_RESULTS','AUDIT_EVENTS','ROUTING_DECISIONS','SETTLEMENT_FILES','REVERSE_PAYMENTS','REFUND_RESOLUTIONS','SETTLEMENT_IMPORTS'):
        assert f'BEFORE UPDATE ON {table}' in text
        assert f'BEFORE DELETE ON {table}' in text


def test_NFR_08_domain_models_are_frozen():
    text=Path('src/paybridge/domain/models.py').read_text()
    assert 'frozen=True' in text
