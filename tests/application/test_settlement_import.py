from datetime import date
from pathlib import Path
from uuid import uuid4
from paybridge.application.settlement_import_service import SettlementImportService
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLiteAuditRepository, SQLiteSettlementRepository
from paybridge.application.audit import AuditService

def test_AC_06_imports_settlement_file(tmp_path):
    pid=uuid4(); path=tmp_path/'input.csv'; path.write_text(f'external_reference,payment_id,amount,currency\next-1,{pid},10.00,INR\n')
    db=Database(tmp_path/'db.sqlite'); service=SettlementImportService(SQLiteSettlementRepository(db),AuditService(SQLiteAuditRepository(db))); entries=service.import_file(path,date.today(),'ops','corr'); assert len(entries)==1
