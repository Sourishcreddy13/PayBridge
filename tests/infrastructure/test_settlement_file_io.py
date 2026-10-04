from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pytest
from paybridge.domain.models import Beneficiary, Payment
from paybridge.domain.enums import BeneficiaryType
from paybridge.infrastructure.settlement_file_io import ImmutableSettlementFileWriter, payment_row
from datetime import datetime, timezone

def payment(): return Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo User'),Decimal('10.00'),'demo','file-idem-1','INR',datetime.now(timezone.utc),'actor')

def test_AC_07_writer_creates_checksum(tmp_path):
    target=tmp_path/'settlement.csv'; checksum=ImmutableSettlementFileWriter().write(target,[payment_row(payment(),'UPI','MATCHED')]); assert target.exists() and len(checksum)==64

def test_AC_07_writer_rejects_overwrite(tmp_path):
    target=tmp_path/'settlement.csv'; writer=ImmutableSettlementFileWriter(); writer.write(target,[]);
    with pytest.raises(FileExistsError): writer.write(target,[])
