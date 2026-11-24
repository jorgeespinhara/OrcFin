"""Transaction CRUD and search."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.change_log import log_change
from core.db.connection import get_connection
from core.models import Transaction, TransactionType

TRANSFER_NOTE = "transfer:internal"
_ACTIVE = " AND deleted_at IS NULL"


def _tx_snapshot(tx: Transaction) -> dict[str, object]:
    return {
        "date": tx.date.isoformat(),
        "description": tx.description,
        "amount": str(tx.amount),
        "category_id": tx.category_id,
        "type": tx.type.value,
        "profile_id": tx.profile_id,
    }


def create_transaction(
    tx: Transaction,
    installment_meta: Optional[Dict[str, Any]] = None,
) -> Transaction:
    conn = get_connection()
    cursor = conn.cursor()
    meta = installment_meta or {}
    cursor.execute("""
        INSERT INTO transactions 
        (profile_id, date, description, amount, category_id, type, is_recurring, notes,
         is_installment, installment_group_id, installment_number, installment_total,
         mei_client_id, credit_card_id, import_batch_id, import_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tx.profile_id,
        tx.date.isoformat(),
        tx.description,
        float(tx.amount),
        tx.category_id,
        tx.type.value,
        int(tx.is_recurring),
        tx.notes,
        int(meta.get("is_installment", tx.is_installment)),
        meta.get("installment_group_id"),
        meta.get("installment_number", tx.installment_number),
        meta.get("installment_total", tx.installment_total),
        tx.mei_client_id,
        tx.credit_card_id,
        tx.import_batch_id,
        getattr(tx, "import_confidence", None),
    ))
    tx.id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_change(
        "transaction",
        "create",
        f"Criado: {tx.description[:48]}",
        entity_id=tx.id,
        new_value=_tx_snapshot(tx),
    )
    return tx


def import_match_key(tx_date: date, amount: Decimal, description: str) -> tuple[str, str, str]:
    from core.engine.recurrence_detection import _normalize_description

    normalized = str(amount.quantize(Decimal("0.01")))
    return (tx_date.isoformat(), normalized, _normalize_description(description))


def existing_import_keys(
    profile_id: int,
    start_date: date,
    end_date: date,
) -> set[tuple[str, str, str]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT date, amount, description FROM transactions
        WHERE profile_id = ? AND date >= ? AND date <= ? AND deleted_at IS NULL
        """,
        (profile_id, start_date.isoformat(), end_date.isoformat()),
    ).fetchall()
    conn.close()
    keys: set[tuple[str, str, str]] = set()
    for row in rows:
        keys.add(
            import_match_key(
                date.fromisoformat(row["date"]),
                Decimal(str(row["amount"])),
                row["description"],
            )
        )
    return keys


def search_transactions(
    query: str,
    *,
    profile_id: Optional[int] = None,
    active_profiles_only: bool = False,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 500,
) -> List[Transaction]:
    needle = query.strip()
    if not needle:
        return get_transactions(
            profile_id=profile_id,
            active_profiles_only=active_profiles_only,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    conn = get_connection()
    sql = f"SELECT * FROM transactions WHERE (description LIKE ? OR IFNULL(notes, '') LIKE ?){_ACTIVE}"
    params: List[Any] = [f"%{needle}%", f"%{needle}%"]

    if profile_id is not None:
        sql += " AND profile_id = ?"
        params.append(profile_id)
    elif active_profiles_only:
        sql += " AND profile_id IN (SELECT id FROM profiles WHERE is_active = 1)"
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date.isoformat())

    sql += " ORDER BY date DESC, created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    transactions = []
    for row in rows:
        row_dict = dict(row)
        row_dict["date"] = date.fromisoformat(row_dict["date"])
        row_dict["amount"] = Decimal(str(row_dict["amount"]))
        row_dict["type"] = TransactionType(row_dict["type"])
        row_dict["is_installment"] = bool(row_dict.get("is_installment", 0))
        transactions.append(Transaction(**row_dict))
    return transactions


def get_transactions(
    profile_id: Optional[int] = None,
    active_profiles_only: bool = False,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    limit: int = 500
) -> List[Transaction]:
    conn = get_connection()
    cursor = conn.cursor()

    query = f"SELECT * FROM transactions WHERE 1=1{_ACTIVE}"
    params: List[Any] = []

    if profile_id is not None:
        query += " AND profile_id = ?"
        params.append(profile_id)
    elif active_profiles_only:
        query += " AND profile_id IN (SELECT id FROM profiles WHERE is_active = 1)"
    if start_date:
        query += " AND date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND date <= ?"
        params.append(end_date.isoformat())
    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)

    query += " ORDER BY date DESC, created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    transactions = []
    for row in rows:
        row_dict = dict(row)
        row_dict["date"] = date.fromisoformat(row_dict["date"])
        row_dict["amount"] = Decimal(str(row_dict["amount"]))
        row_dict["type"] = TransactionType(row_dict["type"])
        row_dict["is_installment"] = bool(row_dict.get("is_installment", 0))
        transactions.append(Transaction(**row_dict))
    return transactions


def update_transaction(tx: Transaction) -> bool:
    if tx.id is None:
        return False
    previous = get_transaction(tx.id)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE transactions SET
                profile_id = ?, date = ?, description = ?, amount = ?,
                category_id = ?, type = ?, is_recurring = ?, notes = ?,
                credit_card_id = ?, mei_client_id = ?
            WHERE id = ? AND deleted_at IS NULL
        """, (
            tx.profile_id, tx.date.isoformat(), tx.description, float(tx.amount),
            tx.category_id, tx.type.value, int(tx.is_recurring), tx.notes,
            tx.credit_card_id, tx.mei_client_id, tx.id,
        ))
        success = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    if success and previous:
        log_change(
            "transaction",
            "update",
            f"Editado: {tx.description[:48]}",
            entity_id=tx.id,
            old_value=_tx_snapshot(previous),
            new_value=_tx_snapshot(tx),
        )
    return success


def delete_transaction(transaction_id: int) -> bool:
    previous = get_transaction(transaction_id)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        success = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    if success and previous:
        log_change(
            "transaction",
            "delete",
            f"Removido: {previous.description[:48]}",
            entity_id=transaction_id,
            old_value=_tx_snapshot(previous),
        )
    return success


def has_transaction_in_category_for_month(
    profile_id: int,
    category_id: int,
    year: int,
    month: int,
) -> bool:
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) as c FROM transactions
            WHERE profile_id = ? AND category_id = ?
              AND date >= ? AND date < ? AND deleted_at IS NULL
            """,
            (profile_id, category_id, start, end),
        ).fetchone()
        return (row["c"] or 0) > 0
    finally:
        conn.close()


def get_transaction(transaction_id: int) -> Optional[Transaction]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND deleted_at IS NULL",
            (transaction_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    row_dict = dict(row)
    row_dict["date"] = date.fromisoformat(row_dict["date"])
    row_dict["amount"] = Decimal(str(row_dict["amount"]))
    row_dict["type"] = TransactionType(row_dict["type"])
    row_dict["is_installment"] = bool(row_dict.get("is_installment", 0))
    return Transaction(**row_dict)


def create_internal_transfer(
    from_profile_id: int,
    to_profile_id: int,
    amount: Decimal,
    description: str,
    tx_date: date,
    expense_category_id: int,
    income_category_id: int,
) -> None:
    if from_profile_id == to_profile_id:
        raise ValueError("Perfis de origem e destino devem ser diferentes")
    note = TRANSFER_NOTE
    from core.db.connection import db_session

    with db_session() as conn:
        try:
            conn.execute(
                """
                INSERT INTO transactions (profile_id, date, description, amount, category_id, type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (from_profile_id, tx_date.isoformat(), description, float(amount), expense_category_id, TransactionType.EXPENSE.value, note),
            )
            conn.execute(
                """
                INSERT INTO transactions (profile_id, date, description, amount, category_id, type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (to_profile_id, tx_date.isoformat(), description, float(amount), income_category_id, TransactionType.INCOME.value, note),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def split_transaction(transaction_id: int, splits: list[tuple[int, Decimal]]) -> int:
    """Replace one transaction with N lines atomically (preserving metadata)."""
    original = get_transaction(transaction_id)
    if not original or not splits:
        return 0
    total = sum((amount for _, amount in splits), Decimal("0"))
    if total != original.amount:
        raise ValueError("A soma das partes deve igualar o valor original")
    from core.db.connection import db_session

    with db_session() as conn:
        try:
            for category_id, amount in splits:
                conn.execute(
                    """
                    INSERT INTO transactions (
                        profile_id, date, description, amount, category_id, type,
                        is_recurring, notes, credit_card_id, mei_client_id,
                        import_batch_id, import_confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        original.profile_id,
                        original.date.isoformat(),
                        original.description,
                        float(amount),
                        category_id,
                        original.type.value,
                        int(original.is_recurring),
                        original.notes,
                        original.credit_card_id,
                        original.mei_client_id,
                        original.import_batch_id,
                        original.import_confidence,
                    ),
                )
            conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return len(splits)


def delete_transactions_batch(transaction_ids: list[int]) -> int:
    """Delete multiple transactions. Returns count removed."""
    if not transaction_ids:
        return 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(transaction_ids))
        cursor.execute(
            f"DELETE FROM transactions WHERE id IN ({placeholders})",
            transaction_ids,
        )
        count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return count


def soft_delete_transactions(transaction_ids: list[int]) -> int:
    """Soft-delete transactions (sets deleted_at) so they can be undone."""
    if not transaction_ids:
        return 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(transaction_ids))
        cursor.execute(
            f"UPDATE transactions SET deleted_at = CURRENT_TIMESTAMP "
            f"WHERE id IN ({placeholders}) AND deleted_at IS NULL",
            transaction_ids,
        )
        count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return count


def restore_transactions(transaction_ids: list[int]) -> int:
    """Restore previously soft-deleted transactions."""
    if not transaction_ids:
        return 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(transaction_ids))
        cursor.execute(
            f"UPDATE transactions SET deleted_at = NULL WHERE id IN ({placeholders})",
            transaction_ids,
        )
        count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return count


def update_transactions_category_batch(transaction_ids: list[int], category_id: int) -> int:
    """Update category_id for multiple transactions at once."""
    if not transaction_ids:
        return 0
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(transaction_ids))
        cursor.execute(
            f"UPDATE transactions SET category_id = ? "
            f"WHERE id IN ({placeholders}) AND deleted_at IS NULL",
            [category_id, *transaction_ids],
        )
        count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return count