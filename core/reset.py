"""Wipe all local financial data and restore factory defaults."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.db.schema import _seed_default_data, init_database

_TABLES_TO_CLEAR = (
    "transactions",
    "mei_invoices",
    "mei_stock_movements",
    "mei_products",
    "mei_subscription_charges",
    "mei_subscriptions",
    "mei_order_outsource",
    "mei_orders",
    "mei_suppliers",
    "import_logs",
    "categorization_rules",
    "budgets",
    "goals",
    "credit_cards",
    "mei_clients",
    "mei_config",
    "assets",
    "liabilities",
    "net_worth_snapshots",
    "profiles",
    "categories",
    "app_settings",
)


def _resolve_db_path() -> Path:
    from core.db.connection import _resolve_db_path as resolve

    return resolve()


def _remove_sidecar_files(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass  # WAL/SHM may be locked on Windows; wipe continues


def _wipe_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    for table in _TABLES_TO_CLEAR:
        cursor.execute(f"DELETE FROM {table}")
    cursor.execute("PRAGMA foreign_keys=ON")
    conn.commit()


def reset_database() -> None:
    """
    Delete every user record (transactions, cards, MEI, budgets, etc.)
    and re-seed default profiles and categories.
    """
    from core.db.connection import get_connection

    db_path = _resolve_db_path()
    _remove_sidecar_files(db_path)

    if not db_path.exists():
        init_database()
        return

    conn = get_connection()
    try:
        _wipe_tables(conn)
        _seed_default_data(conn)
        conn.commit()
    finally:
        conn.close()

    _remove_sidecar_files(db_path)


def reset_clean_install() -> None:
    """Wipe database and settings — equivalent to a fresh install."""
    from core.settings_store import wipe_all_settings

    reset_database()
    wipe_all_settings()