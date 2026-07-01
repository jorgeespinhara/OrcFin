"""Local audit trail for external integration events."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.db.connection import get_connection

_MAX_DETAIL = 600


def log_event(
    event_type: str,
    summary: str,
    *,
    provider: str | None = None,
    detail: str | None = None,
) -> None:
    snippet = None
    if detail:
        snippet = detail[:_MAX_DETAIL]
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO audit_events (event_type, provider, summary, detail)
            VALUES (?, ?, ?, ?)
            """,
            (event_type, provider, summary, snippet),
        )
        conn.commit()
    finally:
        conn.close()


def list_recent_events(limit: int = 25) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, event_type, provider, summary, detail, created_at
            FROM audit_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 100)),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def format_event_line(row: dict[str, Any]) -> str:
    when = row.get("created_at") or ""
    if isinstance(when, str) and "T" not in when:
        try:
            when = datetime.fromisoformat(when).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
    provider = row.get("provider")
    prefix = f"[{when}]"
    if provider:
        prefix += f" {provider}"
    return f"{prefix}: {row.get('summary', '')}"