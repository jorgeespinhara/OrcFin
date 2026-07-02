"""MEI recurring subscriptions and monthly charges."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from core.db.connection import get_connection
from core.models import MeiSubscription, MeiSubscriptionCharge, Transaction, TransactionType


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _charge_due_date(year: int, month: int, due_day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(due_day, last_day))


def create_subscription(sub: MeiSubscription) -> MeiSubscription:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mei_subscriptions (
            profile_id, client_id, name, monthly_amount, due_day,
            start_date, end_date, status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sub.profile_id,
            sub.client_id,
            sub.name.strip(),
            float(sub.monthly_amount),
            sub.due_day,
            sub.start_date.isoformat(),
            sub.end_date.isoformat() if sub.end_date else None,
            sub.status,
            sub.notes,
        ),
    )
    sub.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub


def get_subscriptions(profile_id: int, active_only: bool = False) -> list[dict[str, Any]]:
    conn = get_connection()
    query = "SELECT * FROM mei_subscriptions WHERE profile_id = ?"
    params: list[Any] = [profile_id]
    if active_only:
        query += " AND status = 'active'"
    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_subscription(subscription_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mei_subscriptions WHERE id = ?", (subscription_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_subscription_status(subscription_id: int, status: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mei_subscriptions SET status = ? WHERE id = ?",
        (status, subscription_id),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def _subscription_active_in_month(sub: dict[str, Any], year: int, month: int) -> bool:
    if sub.get("status") != "active":
        return False
    month_start, month_end = _month_bounds(year, month)
    start = date.fromisoformat(str(sub["start_date"])[:10])
    if start > month_end:
        return False
    end_raw = sub.get("end_date")
    if end_raw:
        end = date.fromisoformat(str(end_raw)[:10])
        if end < month_start:
            return False
    return True


def ensure_month_charges(profile_id: int, year: int, month: int) -> None:
    subs = get_subscriptions(profile_id)
    conn = get_connection()
    cursor = conn.cursor()
    for sub in subs:
        if not _subscription_active_in_month(sub, year, month):
            continue
        cursor.execute(
            """
            SELECT id FROM mei_subscription_charges
            WHERE subscription_id = ? AND year = ? AND month = ?
            """,
            (sub["id"], year, month),
        )
        if cursor.fetchone():
            continue
        due = _charge_due_date(year, month, int(sub["due_day"]))
        cursor.execute(
            """
            INSERT INTO mei_subscription_charges (
                subscription_id, year, month, due_date, amount
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (sub["id"], year, month, due.isoformat(), sub["monthly_amount"]),
        )
    conn.commit()
    conn.close()


def list_charges_for_month(
    profile_id: int,
    year: int,
    month: int,
    *,
    unpaid_only: bool = False,
) -> list[dict[str, Any]]:
    ensure_month_charges(profile_id, year, month)
    conn = get_connection()
    query = """
        SELECT c.*, s.name AS subscription_name, s.client_id,
               cl.name AS client_name
        FROM mei_subscription_charges c
        JOIN mei_subscriptions s ON s.id = c.subscription_id
        LEFT JOIN mei_clients cl ON cl.id = s.client_id
        WHERE s.profile_id = ? AND c.year = ? AND c.month = ?
    """
    params: list[Any] = [profile_id, year, month]
    if unpaid_only:
        query += " AND c.paid_at IS NULL"
    query += " ORDER BY c.due_date, s.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_charge(charge_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM mei_subscription_charges WHERE id = ?", (charge_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _income_category_id() -> int | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ? AND type = 'income' LIMIT 1",
        ("Receita MEI",),
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def receive_charge_payment(
    profile_id: int,
    charge_id: int,
    payment_date: date | None = None,
) -> int | None:
    from core.db.repositories.transactions import create_transaction

    charge = get_charge(charge_id)
    if not charge or charge.get("paid_at"):
        return None
    sub = get_subscription(int(charge["subscription_id"]))
    if not sub or sub["profile_id"] != profile_id:
        return None

    cat_id = _income_category_id()
    if not cat_id:
        return None

    pay = payment_date or date.today()
    tx = create_transaction(
        Transaction(
            profile_id=profile_id,
            date=pay,
            description=f"Recorrente {sub.get('name', '')}".strip(),
            amount=Decimal(str(charge["amount"])),
            category_id=cat_id,
            type=TransactionType.INCOME,
            notes=f"subscription_charge:{charge_id}",
        )
    )
    conn = get_connection()
    conn.execute(
        """
        UPDATE mei_subscription_charges
        SET paid_at = ?, transaction_id = ?
        WHERE id = ? AND paid_at IS NULL
        """,
        (pay.isoformat(), tx.id, charge_id),
    )
    conn.commit()
    conn.close()
    return tx.id