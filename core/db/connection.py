"""SQLite connection and PRAGMA configuration."""

from __future__ import annotations

import contextvars
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from core.paths import get_database_path, is_sqlite_database, migrate_legacy_layout

migrate_legacy_layout()

_DB_PATH = get_database_path()

DB_PATH = _DB_PATH

SCHEMA_VERSION = 13


def _resolve_db_path() -> Path:
    """Resolve DB path (patch core.db.connection.DB_PATH in tests)."""
    return DB_PATH


def _quarantine_invalid_db(path: Path) -> None:
    if not path.exists() or is_sqlite_database(path):
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    corrupt = path.with_name(f"{path.stem}.invalid-{stamp}{path.suffix}")
    path.rename(corrupt)


_session_conn: contextvars.ContextVar[sqlite3.Connection | None] = contextvars.ContextVar(
    "db_session_conn", default=None
)


class _SessionConnection:
    __slots__ = ("_conn",)

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def close(self) -> None:
        pass

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


def _open_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    _quarantine_invalid_db(path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection() -> sqlite3.Connection:
    """Get a connection with row factory for easier access."""
    session = _session_conn.get()
    if session is not None:
        return _SessionConnection(session)  # type: ignore[return-value]
    return _open_connection(_resolve_db_path())


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Reuse one SQLite connection for nested get_connection() calls."""
    conn = _open_connection(_resolve_db_path())
    token = _session_conn.set(conn)
    try:
        yield conn
    finally:
        _session_conn.reset(token)
        conn.close()