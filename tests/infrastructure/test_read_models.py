from datetime import UTC, datetime

from paybridge.infrastructure.db import Database
from paybridge.infrastructure.read_models import SQLiteOpsReadModel


def test_ops_read_model_empty(tmp_path):
    model=SQLiteOpsReadModel(Database(tmp_path/'db.sqlite')); assert model.volume_by_status(datetime.now(UTC).date())['PENDING']==0; assert model.volume_by_rail(datetime.now(UTC).date())=={}
