"""Schema v9 change_log snapshots."""

import sqlite3

from core.db.connection import SCHEMA_VERSION


def test_schema_v9_change_log_columns(fresh_db):
    assert SCHEMA_VERSION >= 9
    conn = sqlite3.connect(fresh_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(change_log)").fetchall()}
    assert "old_value_json" in cols
    assert "new_value_json" in cols
    conn.close()