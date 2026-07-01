"""SQLite connection and PRAGMA configuration."""

import sqlite3
from datetime import datetime
from pathlib import Path

from core.branding import DB_FILENAME, LEGACY_DB_FILENAME
from core.paths import get_database_path, is_sqlite_database, migrate_legacy_layout

migrate_legacy_layout()

_DB_PATH = get_database_path()
_LEGACY_DB_PATH = _DB_PATH.parent / LEGACY_DB_FILENAME

DB_PATH = _DB_PATH

SCHEMA_VERSION = 7


def _migrate_legacy_db() -> None:
    if not _DB_PATH.exists() and is_sqlite_database(_LEGACY_DB_PATH):
        _LEGACY_DB_PATH.rename(_DB_PATH)


_migrate_legacy_db()


def _resolve_db_path() -> Path:
    """Resolve DB path (patch core.db.connection.DB_PATH in tests)."""
    return DB_PATH


def _quarantine_invalid_db(path: Path) -> None:
    if not path.exists() or is_sqlite_database(path):
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    corrupt = path.with_name(f"{path.stem}.invalid-{stamp}{path.suffix}")
    path.rename(corrupt)


def get_connection() -> sqlite3.Connection:
    """Get a connection with row factory for easier access."""
    path = _resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _quarantine_invalid_db(path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn