"""Classify transaction origin for audit UI."""

from __future__ import annotations

from typing import Any

from core.db.repositories.import_batches import get_import_batch
from core.db.repositories.transactions import TRANSFER_NOTE
from core.engine.categorization import has_auto_cat_marker
from core.models import Transaction


def describe_transaction_origin(tx: Transaction) -> dict[str, Any]:
    notes = tx.notes or ""
    if tx.import_batch_id:
        batch = get_import_batch(tx.import_batch_id)
        filename = (batch or {}).get("filename") or "arquivo"
        bank = (batch or {}).get("source_bank") or (batch or {}).get("parser_name") or ""
        return {
            "kind": "importação",
            "detail": f"{filename}" + (f" ({bank})" if bank else ""),
            "batch_id": tx.import_batch_id,
        }
    if TRANSFER_NOTE in notes:
        return {"kind": "transferência", "detail": "Entre perfis", "batch_id": None}
    if notes.strip().startswith("installment:"):
        return {"kind": "parcelamento", "detail": "Gerado pelo app", "batch_id": None}
    if tx.is_recurring:
        return {"kind": "recorrência", "detail": "Modelo recorrente", "batch_id": None}
    if tx.mei_client_id:
        return {"kind": "nota fiscal", "detail": "Cliente MEI vinculado", "batch_id": None}
    if has_auto_cat_marker(notes):
        return {"kind": "regra automática", "detail": "Categorização por regra", "batch_id": None}
    if notes.strip().startswith("import:"):
        return {"kind": "importação", "detail": notes.replace("import:", "", 1).strip(), "batch_id": None}
    return {"kind": "manual", "detail": "Cadastro direto", "batch_id": None}