"""SQLite connection and PRAGMA configuration."""

import sqlite3
from pathlib import Path

from core.branding import DB_FILENAME, LEGACY_DB_FILENAME

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_DB_PATH = _DATA_DIR / DB_FILENAME
_LEGACY_DB_PATH = _DATA_DIR / LEGACY_DB_FILENAME


def _migrate_legacy_db() -> None:
    if not _DB_PATH.exists() and _LEGACY_DB_PATH.exists():
        _LEGACY_DB_PATH.rename(_DB_PATH)


_migrate_legacy_db()
DB_PATH = _DB_PATH

SCHEMA_VERSION = 5


def _resolve_db_path() -> Path:
    """Resolve DB path (patch core.db.connection.DB_PATH in tests)."""
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a connection with row factory for easier access."""
    path = _resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn