"""SQLite access. The schema is owned exclusively by the numbered files in ``migrations/``."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def apply_migrations(path: Path, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every unapplied ``NNN_*.sql`` file in order, each inside one transaction."""
    connection = connect(path)
    applied_now: list[str] = []
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        for sql_file in sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql")):
            version = sql_file.stem
            connection.execute("BEGIN IMMEDIATE")
            try:
                done = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=?", (version,)
                ).fetchone()
                if done is None:
                    for statement in _split_statements(sql_file.read_text(encoding="utf-8")):
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                        (version, datetime.now(UTC).isoformat()),
                    )
                    applied_now.append(version)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
    finally:
        connection.close()
    return applied_now


def _split_statements(script: str) -> list[str]:
    """Split a migration script into statements, keeping trigger bodies intact."""
    statements: list[str] = []
    buffer = ""
    for line in script.splitlines():
        if line.strip().startswith("--") and not buffer:
            continue
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Migration ends with an incomplete SQL statement")
    return statements


class Database:
    """Handle to the database file. Migrations run once, when the handle is created."""

    def __init__(self, path: Path) -> None:
        self.path = path
        apply_migrations(path)

    def connection(self) -> sqlite3.Connection:
        return connect(self.path)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a block inside one ``BEGIN IMMEDIATE`` write transaction."""
        connection = self.connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
        finally:
            connection.close()
