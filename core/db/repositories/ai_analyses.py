"""Local history of AI analysis summaries."""

from __future__ import annotations

from typing import Any

from core.db.connection import get_connection


def save_analysis(*, provider: str | None, period_label: str | None, summary: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO ai_analyses (provider, period_label, summary)
            VALUES (?, ?, ?)
            """,
            (provider, period_label, summary[:800]),
        )
        conn.commit()
    finally:
        conn.close()


def list_analyses(*, limit: int = 15) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, provider, period_label, summary, created_at
            FROM ai_analyses
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 50)),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()