"""Credit card repository."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection
from core.models import CreditCard


def create_credit_card(card: CreditCard) -> CreditCard:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO credit_cards
        (profile_id, name, bank, network, last_four, closing_day, due_day, credit_limit, color, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            card.profile_id,
            card.name,
            card.bank,
            card.network,
            card.last_four,
            card.closing_day,
            card.due_day,
            float(card.credit_limit) if card.credit_limit is not None else None,
            card.color,
            int(card.is_active),
        ),
    )
    card.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return card


def update_credit_card(card: CreditCard) -> bool:
    if card.id is None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE credit_cards SET
            name = ?, bank = ?, network = ?, last_four = ?,
            closing_day = ?, due_day = ?, credit_limit = ?, color = ?, is_active = ?
        WHERE id = ?
        """,
        (
            card.name,
            card.bank,
            card.network,
            card.last_four,
            card.closing_day,
            card.due_day,
            float(card.credit_limit) if card.credit_limit is not None else None,
            card.color,
            int(card.is_active),
            card.id,
        ),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def delete_credit_card(card_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET credit_card_id = NULL WHERE credit_card_id = ?", (card_id,))
    cursor.execute("DELETE FROM credit_cards WHERE id = ?", (card_id,))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def get_credit_cards(profile_id: Optional[int] = None, active_only: bool = True) -> List[CreditCard]:
    conn = get_connection()
    query = "SELECT * FROM credit_cards WHERE 1=1"
    params: list[Any] = []
    if profile_id is not None:
        query += " AND profile_id = ?"
        params.append(profile_id)
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY bank, name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_card(dict(row)) for row in rows]


def find_credit_card(
    profile_id: int,
    bank: str,
    last_four: Optional[str] = None,
    network: Optional[str] = None,
) -> Optional[CreditCard]:
    conn = get_connection()
    query = "SELECT * FROM credit_cards WHERE profile_id = ? AND LOWER(bank) = LOWER(?)"
    params: list[Any] = [profile_id, bank]
    if last_four:
        query += " AND last_four = ?"
        params.append(last_four)
    if network:
        query += " AND LOWER(network) = LOWER(?)"
        params.append(network)
    query += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(query, params).fetchone()
    conn.close()
    return _row_to_card(dict(row)) if row else None


def get_card_spending_summary(card_id: int, year: int, month: int) -> Dict[str, Any]:
    conn = get_connection()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE credit_card_id = ? AND type = 'expense'
          AND date >= ? AND date < ?
        """,
        (card_id, start, end),
    ).fetchone()
    conn.close()
    return {
        "transaction_count": row["cnt"],
        "total_expense": Decimal(str(row["total"])),
    }


def _row_to_card(row: dict) -> CreditCard:
    limit = row.get("credit_limit")
    return CreditCard(
        id=row["id"],
        profile_id=row["profile_id"],
        name=row["name"],
        bank=row["bank"],
        network=row["network"],
        last_four=row.get("last_four"),
        closing_day=row.get("closing_day"),
        due_day=row.get("due_day"),
        credit_limit=Decimal(str(limit)) if limit is not None else None,
        color=row.get("color") or "#8B5CF6",
        is_active=bool(row.get("is_active", 1)),
    )