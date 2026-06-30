"""Schema migration tests."""

import sqlite3

import pytest

from core.db.connection import SCHEMA_VERSION
from core.db.migrations import get_schema_version, migrate
from core.db.schema import init_database


@pytest.fixture
def legacy_v1_db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "legacy_v1.db"
    if db_path.exists():
        db_path.unlink()
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA user_version = 1")
    conn.executescript("""
        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#14B8A6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        );
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            icon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, type)
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            is_recurring BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version (version) VALUES (1);
        INSERT INTO profiles (name, color) VALUES ('Legacy', '#14B8A6');
        INSERT INTO categories (name, type, icon) VALUES ('Gasto', 'expense', '📦');
    """)
    conn.commit()
    conn.close()
    return db_path


def test_migrate_v1_to_current(legacy_v1_db):
    conn = sqlite3.connect(legacy_v1_db)
    assert get_schema_version(conn) == 1
    migrate(conn, 1, SCHEMA_VERSION)
    conn.commit()

    cols = {row[1] for row in conn.execute("PRAGMA table_info(profiles)").fetchall()}
    assert "profile_type" in cols

    cat_cols = {row[1] for row in conn.execute("PRAGMA table_info(categories)").fetchall()}
    assert "is_mei_deductible" in cat_cols

    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "mei_config" in tables
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_init_database_upgrades_legacy(legacy_v1_db):
    init_database()
    conn = sqlite3.connect(legacy_v1_db)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()
    conn = sqlite3.connect(legacy_v1_db)
    assert "mei_invoices" in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()