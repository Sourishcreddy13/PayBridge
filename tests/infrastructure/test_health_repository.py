from paybridge.infrastructure.db import Database
from paybridge.infrastructure.health_repository import SQLiteHealthRepository


def test_health_repository_executes_select(tmp_path):
    SQLiteHealthRepository(Database(tmp_path / "db.sqlite")).check()
