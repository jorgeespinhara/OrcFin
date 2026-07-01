"""Schema v8 tables."""

import sqlite3

from core.db.connection import SCHEMA_VERSION


def test_schema_v8_tables(fresh_db):
    assert SCHEMA_VERSION == 8
    conn = sqlite3.connect(fresh_db)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "import_templates" in tables
    assert "change_log" in tables
    assert "dismissed_insights" in tables
    assert "ai_analyses" in tables
    cols = {row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    assert "deleted_at" in cols
    assert "import_confidence" in cols
    conn.close()