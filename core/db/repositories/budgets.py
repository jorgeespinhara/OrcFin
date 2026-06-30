"""Monthly budget limits by category."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection


def set_budget(profile_id: Optional[int], category_id: int, year: int, month: int, limit_amount: float) -> bool:
    """Create or update monthly budget for a category."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO budgets (profile_id, category_id, year, month, monthly_limit)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(profile_id, category_id, year, month) DO UPDATE SET monthly_limit = excluded.monthly_limit
    """, (profile_id, category_id, year, month, limit_amount))
    conn.commit()
    conn.close()
    return True


def get_budgets_for_month(year: int, month: int, profile_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get budgets + actual spending for the month."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            b.id,
            b.category_id,
            c.name as category_name,
            c.icon,
            b.monthly_limit,
            COALESCE(SUM(t.amount), 0) as spent
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON t.category_id = b.category_id 
            AND strftime('%Y', t.date) = ? 
            AND strftime('%m', t.date) = ?
    """
    params = [str(year), f"{month:02d}"]

    if profile_id is not None:
        query += " AND (b.profile_id = ? OR b.profile_id IS NULL) AND (t.profile_id = ? OR t.profile_id IS NULL)"
        params.extend([profile_id, profile_id])
    else:
        query += " AND (b.profile_id IS NULL)"

    query += " GROUP BY b.id ORDER BY b.monthly_limit DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        spent = Decimal(str(row["spent"]))
        limit_ = Decimal(str(row["monthly_limit"]))
        remaining = limit_ - spent
        pct = float((spent / limit_ * 100)) if limit_ > 0 else 0

        result.append({
            "id": row["id"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
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
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_consolidated_budgets_for_month(year: int, month: int) -> List[Dict[str, Any]]:
    """Aggregate budgets and spending across all active profiles by category."""
    from core.db.repositories.profiles import get_all_profiles

    merged: Dict[int, Dict[str, Any]] = {}
    for profile in get_all_profiles():
        for budget in get_budgets_for_month(year, month, profile.id):
            cid = budget["category_id"]
            if cid not in merged:
                merged[cid] = {
                    "id": budget["id"],
                    "category_id": cid,
                    "category_name": budget["category_name"],
                    "icon": budget["icon"],
                    "limit": Decimal("0"),
                    "spent": Decimal("0"),
                }
            merged[cid]["limit"] += budget["limit"]
            merged[cid]["spent"] += budget["spent"]

    result = []
    for item in merged.values():
        limit_ = item["limit"]
        spent = item["spent"]
        pct = float((spent / limit_ * 100)) if limit_ > 0 else 0
        result.append({
            **item,
            "remaining": limit_ - spent,
            "percentage": min(round(pct, 1), 100),
            "status": "over" if spent > limit_ else ("warning" if pct > 80 else "ok"),
        })
    result.sort(key=lambda x: x["limit"], reverse=True)
    return result