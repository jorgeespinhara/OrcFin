"""Dismissed dashboard insight keys per profile."""

from __future__ import annotations

from core.db.connection import get_connection


def dismiss_insight(profile_id: int | None, insight_key: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO dismissed_insights (profile_id, insight_key)
            VALUES (?, ?)
            """,
            (profile_id, insight_key),
        )
        conn.commit()
    finally:
        conn.close()


def dismissed_keys(profile_id: int | None) -> set[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT insight_key FROM dismissed_insights
            WHERE profile_id IS ? OR profile_id = ?
            """,
            (profile_id, profile_id),
        ).fetchall()
        return {row["insight_key"] for row in rows}
    finally:
        conn.close()