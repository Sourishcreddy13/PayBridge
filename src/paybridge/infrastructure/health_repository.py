import sqlite3
from pathlib import Path

from .db import Database


class SQLiteHealthRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def check(self) -> None:
        connection = self._database.connection()
        try:
            connection.execute("SELECT 1").fetchone()
        except sqlite3.Error as exc:
            raise RuntimeError("Database health check failed") from exc
        finally:
            connection.close()

    def ensure_path(self) -> Path:
        path = self._database.path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
