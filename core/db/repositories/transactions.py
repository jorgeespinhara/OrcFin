"""Transaction CRUD and search."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.change_log import log_change
from core.db.connection import get_connection
from core.models import Transaction, TransactionType

TRANSFER_NOTE = "transfer:internal"
_ACTIVE = " AND deleted_at IS NULL"


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


def log_import(filename: str, count: int, profile_id: Optional[int] = None) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO import_logs (filename, transactions_imported, profile_id)
        VALUES (?, ?, ?)
        """,
        (filename, count, profile_id),
    )
    conn.commit()
    conn.close()


def update_transaction(tx: Transaction) -> bool:
    if tx.id is None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE transactions SET
            profile_id = ?, date = ?, description = ?, amount = ?,
            category_id = ?, type = ?, is_recurring = ?, notes = ?, credit_card_id = ?
        WHERE id = ?
    """, (
        tx.profile_id, tx.date.isoformat(), tx.description, float(tx.amount),
        tx.category_id, tx.type.value, int(tx.is_recurring), tx.notes,
        tx.credit_card_id, tx.id,
    ))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if success:
        log_change(
            "transaction",
            "update",
            f"Editado: {tx.description[:48]}",
            entity_id=tx.id,
        )
    return success


def delete_transaction(transaction_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if success:
        log_change("transaction", "delete", "Lançamento removido", entity_id=transaction_id)
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
    row = conn.execute(
        """
        SELECT COUNT(*) as c FROM transactions
        WHERE profile_id = ? AND category_id = ? AND date >= ? AND date < ?
        """,
        (profile_id, category_id, start, end),
    ).fetchone()
    conn.close()
    return (row["c"] or 0) > 0


def get_transaction(transaction_id: int) -> Optional[Transaction]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
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
    create_transaction(
        Transaction(
            profile_id=from_profile_id,
            date=tx_date,
            description=description,
            amount=amount,
            category_id=expense_category_id,
            type=TransactionType.EXPENSE,
            notes=note,
        )
    )
    create_transaction(
        Transaction(
            profile_id=to_profile_id,
            date=tx_date,
            description=description,
            amount=amount,
            category_id=income_category_id,
            type=TransactionType.INCOME,
            notes=note,
        )
    )


def split_transaction(transaction_id: int, splits: list[tuple[int, Decimal]]) -> int:
    """Replace one transaction with N lines (same date/description/type)."""
    original = get_transaction(transaction_id)
    if not original or not splits:
        return 0
    total = sum(amount for _, amount in splits)
    if total != original.amount:
        raise ValueError("A soma das partes deve igualar o valor original")
    created = 0
    for category_id, amount in splits:
        create_transaction(
            Transaction(
                profile_id=original.profile_id,
                date=original.date,
                description=original.description,
                amount=amount,
                category_id=category_id,
                type=original.type,
                notes=original.notes,
                credit_card_id=original.credit_card_id,
            )
        )
        created += 1
    delete_transaction(transaction_id)
    return created


def delete_transactions_batch(transaction_ids: list[int]) -> int:
    """Delete multiple transactions. Returns count removed."""
    if not transaction_ids:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(transaction_ids))
    cursor.execute(
        f"DELETE FROM transactions WHERE id IN ({placeholders})",
        transaction_ids,
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count