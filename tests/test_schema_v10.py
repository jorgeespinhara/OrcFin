"""Schema v10 investment tables."""

import sqlite3

from core.db.connection import SCHEMA_VERSION


def test_schema_v10_investment_tables(fresh_db):
    assert SCHEMA_VERSION == 10
    conn = sqlite3.connect(fresh_db)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "investment_holdings" in tables
    assert "investment_quotes" in tables
    assert "investment_snapshots" in tables
    cols = {row[1] for row in conn.execute("PRAGMA table_info(investment_holdings)").fetchall()}
    assert "asset_class" in cols
    assert "cnpj" in cols
    assert "applied_at" in cols
    conn.close()