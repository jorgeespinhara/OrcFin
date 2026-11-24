"""Monthly budget limits by category."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection


def set_budget(profile_id: Optional[int], category_id: int, year: int, month: int, limit_amount: float) -> bool:
    """Create or update monthly budget for a category (handles NULL profile_id safely)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if profile_id is None:
            existing = cursor.execute(
                """
                SELECT id FROM budgets
                WHERE profile_id IS NULL AND category_id = ? AND year = ? AND month = ?
                LIMIT 1
                """,
                (category_id, year, month),
            ).fetchone()
            if existing:
                cursor.execute(
                    "UPDATE budgets SET monthly_limit = ? WHERE id = ?",
                    (limit_amount, existing["id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO budgets (profile_id, category_id, year, month, monthly_limit)
                    VALUES (NULL, ?, ?, ?, ?)
                    """,
                    (category_id, year, month, limit_amount),
                )
        else:
            cursor.execute(
                """
                INSERT INTO budgets (profile_id, category_id, year, month, monthly_limit)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, category_id, year, month)
                DO UPDATE SET monthly_limit = excluded.monthly_limit
                """,
                (profile_id, category_id, year, month, limit_amount),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def _month_date_range(year: int, month: int) -> tuple[str, str]:
    start = f"{year}-{month:02d}-01"
    end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    return start, end


def get_budgets_for_month(year: int, month: int, profile_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get budgets + actual spending for the month."""
    start, end = _month_date_range(year, month)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if profile_id is not None:
            query = """
                SELECT
                    b.id,
                    b.category_id,
                    c.name as category_name,
                    c.slug as category_slug,
                    c.icon,
                    b.monthly_limit,
                    COALESCE(SUM(t.amount), 0) as spent
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                LEFT JOIN transactions t ON t.category_id = b.category_id
                    AND t.type = 'expense'
                    AND t.deleted_at IS NULL
                    AND t.date >= ? AND t.date < ?
                    AND t.profile_id = ?
                WHERE b.year = ? AND b.month = ?
                  AND (b.profile_id = ? OR b.profile_id IS NULL)
                GROUP BY b.id
                ORDER BY b.monthly_limit DESC
            """
            params = [start, end, profile_id, year, month, profile_id]
        else:
            query = """
                SELECT
                    b.id,
                    b.category_id,
                    c.name as category_name,
                    c.slug as category_slug,
                    c.icon,
                    b.monthly_limit,
                    COALESCE(SUM(t.amount), 0) as spent
                FROM budgets b
                JOIN categories c ON b.category_id = c.id
                LEFT JOIN transactions t ON t.category_id = b.category_id
                    AND t.type = 'expense'
                    AND t.deleted_at IS NULL
                    AND t.date >= ? AND t.date < ?
                    AND t.profile_id IN (SELECT id FROM profiles WHERE is_active = 1)
                WHERE b.year = ? AND b.month = ?
                  AND b.profile_id IS NULL
                GROUP BY b.id
                ORDER BY b.monthly_limit DESC
            """
            params = [start, end, year, month]

        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        conn.close()

    from core.categories_catalog import category_label

    result = []
    for row in rows:
        spent = Decimal(str(row["spent"]))
        limit_ = Decimal(str(row["monthly_limit"]))
        remaining = limit_ - spent
        pct = float((spent / limit_ * 100)) if limit_ > 0 else 0

        result.append({
            "id": row["id"],
            "category_id": row["category_id"],
            "category_name": category_label(row["category_slug"], row["category_name"]),
            "icon": row["icon"] or "📦",
            "limit": limit_,
            "spent": spent,
            "remaining": remaining,
            "percentage": min(round(pct, 1), 100),
            "status": "over" if spent > limit_ else ("warning" if pct > 80 else "ok")
        })
    return result


def delete_budget(budget_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_consolidated_budgets_for_month(year: int, month: int) -> List[Dict[str, Any]]:
    """Aggregate budgets and spending across all active profiles by category (without double-counting global budgets)."""
    start, end = _month_date_range(year, month)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                MIN(b.id) AS id,
                b.category_id,
                c.name AS category_name,
                c.slug AS category_slug,
                c.icon,
                SUM(b.monthly_limit) AS total_limit,
                COALESCE((
                    SELECT SUM(t.amount)
                    FROM transactions t
                    WHERE t.category_id = b.category_id
                      AND t.type = 'expense'
                      AND t.deleted_at IS NULL
                      AND t.date >= ? AND t.date < ?
                      AND t.profile_id IN (SELECT id FROM profiles WHERE is_active = 1)
                ), 0) AS spent
            FROM budgets b
            JOIN categories c ON b.category_id = c.id
            WHERE b.year = ? AND b.month = ?
              AND (b.profile_id IS NULL OR b.profile_id IN (SELECT id FROM profiles WHERE is_active = 1))
            GROUP BY b.category_id
            ORDER BY total_limit DESC
            """,
            (start, end, year, month),
        ).fetchall()
    finally:
        conn.close()

    from core.categories_catalog import category_label

    result = []
    for row in rows:
        limit_ = Decimal(str(row["total_limit"]))
        spent = Decimal(str(row["spent"]))
        pct = float((spent / limit_ * 100)) if limit_ > 0 else 0
        result.append({
            "id": row["id"],
            "category_id": row["category_id"],
            "category_name": category_label(row["category_slug"], row["category_name"]),
            "icon": row["icon"] or "📦",
            "limit": limit_,
            "spent": spent,
            "remaining": limit_ - spent,
            "percentage": min(round(pct, 1), 100),
            "status": "over" if spent > limit_ else ("warning" if pct > 80 else "ok"),
        })
    return result