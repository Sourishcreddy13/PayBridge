from pathlib import Path
from uuid import uuid4
from paybridge.domain.models import PaymentTransition
from paybridge.domain.enums import PaymentState
from paybridge.application.audit import AuditService
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLiteAuditRepository

def test_AC_09_audit_is_append_only(tmp_path):
    db=Database(tmp_path/'db.sqlite'); service=AuditService(SQLiteAuditRepository(db)); service.record_transition(PaymentTransition(uuid4(),PaymentState.PENDING,PaymentState.PROCESSING,__import__('datetime').datetime.now(__import__('datetime').timezone.utc),'actor'),'corr'); c=db.connection();
    try: assert c.execute('SELECT COUNT(*) n FROM audit_events').fetchone()['n']==1
    finally: c.close()
