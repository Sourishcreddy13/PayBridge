from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from paybridge.domain.enums import BeneficiaryType
from paybridge.domain.models import Beneficiary, Payment
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.read_models import SQLiteOpsReadModel
from paybridge.infrastructure.repositories import SQLitePaymentRepository, SQLiteRoutingRepository
from paybridge.domain.models import RoutingDecision
from paybridge.domain.enums import Rail

def test_ops_read_model_empty(tmp_path):
    model=SQLiteOpsReadModel(Database(tmp_path/'db.sqlite')); assert model.volume_by_status(datetime.now(timezone.utc).date())['PENDING']==0; assert model.volume_by_rail(datetime.now(timezone.utc).date())=={}
