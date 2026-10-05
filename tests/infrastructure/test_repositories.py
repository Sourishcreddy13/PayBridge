from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.models import Beneficiary, Payment
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.repositories import SQLitePaymentRepository


def make_payment(idem='repo-idem-1'):
    return Payment(uuid4(), Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo'), Decimal('12.34'), 'demo', idem, 'INR', datetime.now(UTC), 'actor')


def test_AC_01_append_and_read(tmp_path):
    repo=SQLitePaymentRepository(Database(tmp_path/'db.sqlite')); p=make_payment(); repo.reserve_and_append_payment(p); assert repo.get_payment(p.payment_id).amount == Decimal('12.34')


def test_AC_02_replay_returns_original(tmp_path):
    repo=SQLitePaymentRepository(Database(tmp_path/'db.sqlite')); p=make_payment(); assert repo.reserve_and_append_payment(p)==(True,p.payment_id); replay=make_payment('repo-idem-1'); assert repo.reserve_and_append_payment(replay)==(False,p.payment_id)
