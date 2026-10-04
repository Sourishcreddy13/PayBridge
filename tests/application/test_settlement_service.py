from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from paybridge.application.settlement_service import SettlementService
from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus
from paybridge.domain.models import Beneficiary, Payment, SettlementEntry

class Payments:
    def __init__(self,p): self.p=p
    def list_settled(self,d): return self.p
    def get_current_state(self,pid): return PaymentState.SETTLED
class Routes:
    def get_route(self,pid): return Rail.UPI
class Settlements:
    def __init__(self): self.exists=False; self.files=[]
    def settlement_exists(self,d): return self.exists
    def list_reconciliation_results(self,d): return [SettlementEntry('ext',None,Decimal('10'),'INR',d,ReconciliationStatus.UNMATCHED)]
    def append_file_record(self,d,path,checksum): self.files.append((d,path,checksum))

def make_payment(day):
    return Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo User'),Decimal('10.00'),'demo','settle-test-1','INR',datetime.combine(day,datetime.min.time(),timezone.utc),'actor')

def test_AC_07_generates_immutable_file(tmp_path):
    day=date(2026,10,4); repo=Settlements(); service=SettlementService(Payments([make_payment(day)]),Routes(),repo,tmp_path); target=service.generate(day); text=target.read_text(); assert 'MATCHED' in text or 'UNMATCHED' in text; assert repo.files

def test_AC_07_existing_file_conflicts(tmp_path):
    day=date(2026,10,4); target=tmp_path/'settlement-2026-10-04.csv'; target.write_text('existing'); repo=Settlements(); service=SettlementService(Payments([make_payment(day)]),Routes(),repo,tmp_path)
    import pytest
    with pytest.raises(Exception): service.generate(day)
