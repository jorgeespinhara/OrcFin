"""Import batch tracking and rollback."""

from __future__ import annotations

from typing import Any

from datetime import datetime

from core.change_log import log_change
from core.db.connection import get_connection
from core.import_parsers.registry import parser_version as registry_parser_version
STATUS_COMPLETED = "completed"
STATUS_ROLLED_BACK = "rolled_back"


def create_import_batch(
    *,
    profile_id: int,
    filename: str,
    source_type: str | None,
    source_bank: str | None,
    parser_name: str | None,
    parser_id: str | None = None,
    file_hash: str | None,
    rows_total: int,
    rows_imported: int,
    rows_skipped: int,
    notes: str | None = None,
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO import_batches (
                profile_id, source_type, source_bank, filename, file_hash,
                parser_name, parser_version, rows_total, rows_imported,
                rows_skipped, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                source_type,
                source_bank,
                filename,
                file_hash,
                parser_name,
                registry_parser_version(parser_id or "generic_csv"),
                rows_total,
                rows_imported,
                rows_skipped,
                STATUS_COMPLETED,
                notes,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def list_import_batches(profile_id: int, *, limit: int = 30) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, created_at, source_type, source_bank, filename, parser_name,
                   rows_total, rows_imported, rows_skipped, status
            FROM import_batches
            WHERE profile_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (profile_id, max(1, min(limit, 100))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_batch_imported_count(batch_id: int, rows_imported: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE import_batches SET rows_imported = ? WHERE id = ?",
            (rows_imported, batch_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_import_batch(batch_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM import_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def count_batch_transactions(batch_id: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM transactions
            WHERE import_batch_id = ? AND deleted_at IS NULL
            """,
            (batch_id,),
        ).fetchone()
        return int(row["c"] or 0)
    finally:
        conn.close()


def rollback_import_batch(batch_id: int, *, profile_id: int) -> int:
    batch = get_import_batch(batch_id)
    if not batch:
        raise ValueError("Lote de importação não encontrado.")
    if batch["profile_id"] != profile_id:
        raise ValueError("Este lote pertence a outro perfil.")
    if batch["status"] == STATUS_ROLLED_BACK:
        raise ValueError("Esta importação já foi desfeita.")

    conn = get_connection()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        updated = conn.execute(
            """
            UPDATE transactions SET deleted_at = ?
            WHERE import_batch_id = ? AND profile_id = ? AND deleted_at IS NULL
            """,
            (now, batch_id, profile_id),
        ).rowcount
        conn.execute(
            "UPDATE import_batches SET status = ? WHERE id = ?",
            (STATUS_ROLLED_BACK, batch_id),
        )
        conn.commit()
        log_change(
            "import",
            "rollback",
            f"Desfeitos {updated} lançamentos do lote {batch_id}",
            entity_id=batch_id,
        )
        return updated
    finally:
        conn.close()