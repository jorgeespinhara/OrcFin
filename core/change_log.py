"""Local change trail for imports, backups and data edits."""

from __future__ import annotations

import json
from typing import Any

from core.db.connection import get_connection

_MAX_DETAIL = 400
_MAX_JSON = 2000


def _json_snippet(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)[:_MAX_JSON]


def log_change(
    entity: str,
    action: str,
    summary: str,
    *,
    entity_id: int | None = None,
    detail: str | None = None,
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    snippet = detail[:_MAX_DETAIL] if detail else None
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO change_log (
                entity, entity_id, action, summary, detail, old_value_json, new_value_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity,
                entity_id,
                action,
                summary,
                snippet,
                _json_snippet(old_value),
                _json_snippet(new_value),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_changes_for_entity(entity: str, entity_id: int, *, limit: int = 10) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, entity, entity_id, action, summary, detail,
                   old_value_json, new_value_json, created_at
            FROM change_log
            WHERE entity = ? AND entity_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (entity, entity_id, max(1, min(limit, 50))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_recent_changes(limit: int = 25) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, entity, entity_id, action, summary, detail,
                   old_value_json, new_value_json, created_at
            FROM change_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 100)),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def format_change_line(row: dict[str, Any]) -> str:
    when = row.get("created_at") or ""
    entity = row.get("entity") or ""
    action = row.get("action") or ""
    return f"[{when}] {entity}/{action}: {row.get('summary', '')}"