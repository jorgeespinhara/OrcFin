"""Saved CSV column mappings."""

from __future__ import annotations

from typing import Any

from core.db.connection import get_connection


def save_template(
    *,
    name: str,
    date_col: str,
    desc_col: str,
    amount_col: str | None = None,
    debit_col: str | None = None,
    credit_col: str | None = None,
    sep: str | None = None,
    profile_id: int | None = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO import_templates (
                profile_id, name, date_col, desc_col, amount_col, debit_col, credit_col, sep
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (profile_id, name.strip(), date_col, desc_col, amount_col, debit_col, credit_col, sep),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_templates(profile_id: int | None = None, *, limit: int = 20) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        if profile_id is not None:
            rows = conn.execute(
                """
                SELECT * FROM import_templates
                WHERE profile_id IS NULL OR profile_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (profile_id, max(1, min(limit, 50))),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM import_templates ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 50)),),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()