"""Incremental SQLite schema migrations (PRAGMA user_version)."""

from __future__ import annotations

import sqlite3

from core.db.connection import SCHEMA_VERSION


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read effective schema version (PRAGMA user_version + legacy schema_version table)."""
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    table_version = 0
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row:
            table_version = int(row[0])
    except sqlite3.OperationalError:
        pass
    return max(user_version, table_version)


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)}")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)
        """
    )
    count = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    else:
        conn.execute("UPDATE schema_version SET version = ?", (version,))


def _add_column(cursor: sqlite3.Cursor, table: str, column: str, typedef: str) -> None:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")
    except sqlite3.OperationalError:
        pass


def migrate(conn: sqlite3.Connection, from_version: int, to_version: int = SCHEMA_VERSION) -> None:
    """Apply incremental migrations from from_version to to_version."""
    cursor = conn.cursor()

    if from_version < 2 <= to_version:
        for col, typedef in [
            ("is_installment", "INTEGER DEFAULT 0"),
            ("installment_group_id", "TEXT"),
            ("installment_number", "INTEGER"),
            ("installment_total", "INTEGER"),
        ]:
            _add_column(cursor, "transactions", col, typedef)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorization_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                priority INTEGER DEFAULT 100,
                match_type TEXT NOT NULL CHECK(match_type IN ('contains', 'starts_with', 'equals')),
                pattern TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                profile_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        """)

    if from_version < 3 <= to_version:
        _add_column(cursor, "profiles", "profile_type", "TEXT DEFAULT 'personal'")
        _add_column(cursor, "categories", "is_mei_deductible", "INTEGER DEFAULT 0")
        _add_column(cursor, "transactions", "mei_client_id", "INTEGER")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mei_config (
                profile_id INTEGER PRIMARY KEY,
                razao_social TEXT NOT NULL,
                cnpj TEXT NOT NULL,
                activity_type TEXT NOT NULL CHECK(activity_type IN ('comercio', 'servico', 'industria', 'comercio_servico')),
                custom_das_amount REAL,
                annual_limit REAL DEFAULT 81000,
                das_day INTEGER DEFAULT 20,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mei_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                document TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mei_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                invoice_number TEXT NOT NULL,
                client_id INTEGER,
                tomador_name TEXT,
                amount REAL NOT NULL,
                issue_date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (client_id) REFERENCES mei_clients(id) ON DELETE SET NULL
            )
        """)

    if from_version < 4 <= to_version:
        for col, typedef in [
            ("due_date", "DATE"),
            ("paid_at", "DATE"),
            ("transaction_id", "INTEGER"),
        ]:
            _add_column(cursor, "mei_invoices", col, typedef)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'other',
                current_value REAL NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                liability_type TEXT NOT NULL DEFAULT 'other',
                current_balance REAL NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                total_assets REAL NOT NULL DEFAULT 0,
                total_liabilities REAL NOT NULL DEFAULT 0,
                net_worth REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(profile_id, snapshot_date),
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)

    if from_version < 5 <= to_version:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                bank TEXT NOT NULL,
                network TEXT NOT NULL DEFAULT 'Mastercard',
                last_four TEXT,
                closing_day INTEGER,
                due_day INTEGER,
                credit_limit REAL,
                color TEXT DEFAULT '#8B5CF6',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        _add_column(cursor, "transactions", "credit_card_id", "INTEGER")

    if from_version < 6 <= to_version:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                provider TEXT,
                summary TEXT NOT NULL,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if from_version < 7 <= to_version:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_type TEXT,
                source_bank TEXT,
                filename TEXT NOT NULL,
                file_hash TEXT,
                parser_name TEXT,
                parser_version TEXT DEFAULT '1',
                rows_total INTEGER DEFAULT 0,
                rows_imported INTEGER DEFAULT 0,
                rows_skipped INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'completed',
                notes TEXT,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        _add_column(cursor, "transactions", "import_batch_id", "INTEGER")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_import_batch "
            "ON transactions(import_batch_id)"
        )

    if from_version < 8 <= to_version:
        _add_column(cursor, "transactions", "deleted_at", "TIMESTAMP")
        _add_column(cursor, "transactions", "import_confidence", "TEXT")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                name TEXT NOT NULL,
                date_col TEXT NOT NULL,
                desc_col TEXT NOT NULL,
                amount_col TEXT,
                debit_col TEXT,
                credit_col TEXT,
                sep TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                entity_id INTEGER,
                action TEXT NOT NULL,
                summary TEXT NOT NULL,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dismissed_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                insight_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(profile_id, insight_key)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT,
                period_label TEXT,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if from_version < 9 <= to_version:
        _add_column(cursor, "change_log", "old_value_json", "TEXT")
        _add_column(cursor, "change_log", "new_value_json", "TEXT")

    if from_version < to_version:
        set_schema_version(conn, to_version)