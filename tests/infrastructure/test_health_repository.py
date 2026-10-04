from paybridge.infrastructure.db import Database
from paybridge.infrastructure.health_repository import SQLiteHealthRepository

def test_health_repository_executes_select(tmp_path):
    repo=SQLiteHealthRepository(Database(tmp_path/'db.sqlite')); repo.check(); assert repo.ensure_path().name=='db.sqlite'
