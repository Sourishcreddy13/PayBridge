from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.models import Beneficiary, Payment
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLitePaymentRepository


def test_NFR_03_persistence_stores_only_masked_beneficiary_data(tmp_path):
    db=Database(tmp_path/'pii.db'); repo=SQLitePaymentRepository(db); p=Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo User'),Decimal(10),'demo','pii-idem-1','INR',datetime.now(UTC),'actor'); repo.reserve_and_append_payment(p); c=db.connection()
    try:
        row=c.execute('SELECT account_masked,ifsc_masked,beneficiary_name_masked FROM payments WHERE payment_id=?',(str(p.payment_id),)).fetchone(); assert row['account_masked'].endswith('9012'); assert 'ABCD0123456' not in row['ifsc_masked']; assert row['beneficiary_name_masked']=='D*** U***'
    finally: c.close()

def test_NFR_03_plain_account_is_not_in_persisted_row(tmp_path):
    db=Database(tmp_path/'pii2.db'); repo=SQLitePaymentRepository(db); p=Payment(uuid4(),Beneficiary('987654321098','WXYZ0987654',BeneficiaryType.CORPORATE,'Demo User'),Decimal(11),'demo','pii-idem-2','INR',datetime.now(UTC),'actor'); repo.reserve_and_append_payment(p); c=db.connection()
    try:
        row=c.execute('SELECT account_masked FROM payments WHERE payment_id=?',(str(p.payment_id),)).fetchone(); assert row['account_masked']!='987654321098'
    finally: c.close()
