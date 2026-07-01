"""Aggregation and reporting SQL queries."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.domain.month_format import format_month_year_label
from core.db.connection import get_connection
from core.db.repositories.profiles import get_all_profiles
from core.models import TransactionType


_TRANSFER_EXCLUDE = " AND IFNULL(t.notes, '') NOT LIKE 'transfer:%'"
_TX_ACTIVE = " AND deleted_at IS NULL"
_TX_T_ACTIVE = " AND t.deleted_at IS NULL"


def _month_bounds(year: int, month: int) -> Tuple[str, str]:
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    return start, end


def _recurring_series_key(profile_id: int, category_id: int, description: str) -> tuple[int, int, str]:
    return profile_id, category_id, description.lower().strip()


def _month_is_past(year: int, month: int) -> bool:
    today = date.today()
    return (year, month) < (today.year, today.month)


def get_recurring_templates(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> List[Dict[str, Any]]:
    """Latest recurring transaction per profile/category/description series."""
    conn = get_connection()
    query = f"""
        SELECT
            t.profile_id,
            t.description,
            t.amount,
            t.category_id,
            t.type,
            t.date,
            c.name,
            c.icon
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.is_recurring = 1{_TX_T_ACTIVE}
    """
    params: List[Any] = []
    if consolidated:
        query += " AND t.profile_id IN (SELECT id FROM profiles WHERE is_active = 1)"
    elif profile_id is not None:
        query += " AND t.profile_id = ?"
        params.append(profile_id)

    query += " ORDER BY t.date DESC, t.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    seen: set[tuple[int, int, str]] = set()
    templates: List[Dict[str, Any]] = []
    for row in rows:
        key = _recurring_series_key(row["profile_id"], row["category_id"], row["description"])
        if key in seen:
            continue
        seen.add(key)
        templates.append({
            "profile_id": row["profile_id"],
            "description": row["description"],
            "amount": Decimal(str(row["amount"])),
            "category_id": row["category_id"],
            "type": row["type"],
            "date": row["date"],
            "name": row["name"],
            "icon": row["icon"] or "📦",
        })
    return templates


def _logged_series_keys_in_month(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> set[tuple[int, int, str]]:
    start, end = _month_bounds(year, month)
    conn = get_connection()
    query = f"""
        SELECT t.profile_id, t.category_id, t.description
        FROM transactions t
        WHERE t.date >= ? AND t.date < ?{_TX_T_ACTIVE}
    """
    params: List[Any] = [start, end]
    if consolidated:
        query += " AND t.profile_id IN (SELECT id FROM profiles WHERE is_active = 1)"
    elif profile_id is not None:
        query += " AND t.profile_id = ?"
        params.append(profile_id)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {
        _recurring_series_key(r["profile_id"], r["category_id"], r["description"])
        for r in rows
    }


def _pending_recurring_for_month(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    type_filter: Optional[TransactionType] = None,
) -> List[Dict[str, Any]]:
    if _month_is_past(year, month):
        return []

    logged = _logged_series_keys_in_month(year, month, profile_id, consolidated)
    pending: List[Dict[str, Any]] = []
    for template in get_recurring_templates(profile_id, consolidated):
        if type_filter is not None and template["type"] != type_filter.value:
            continue
        started = date.fromisoformat(str(template["date"]))
        if (started.year, started.month) > (year, month):
            continue
        key = _recurring_series_key(
            template["profile_id"],
            template["category_id"],
            template["description"],
        )
        if key not in logged:
            pending.append(template)
    return pending


def get_monthly_summary(
    year: int,
    month: int,
    profile_id: Optional[int] = None
) -> Dict[str, Any]:
    """Return income, expense, net for a specific month (optionally per profile)."""
    conn = get_connection()
    cursor = conn.cursor()

    start, end = _month_bounds(year, month)

    base_query = f"""
        SELECT 
            type,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions
        WHERE date >= ? AND date < ?{_TX_ACTIVE}
    """
    params: List[Any] = [start, end]

    if profile_id is not None:
        base_query += " AND profile_id = ?"
        params.append(profile_id)

    base_query += " GROUP BY type"

    cursor.execute(base_query, params)
    rows = cursor.fetchall()

    income = Decimal("0")
    expense = Decimal("0")
    tx_count = 0

    for row in rows:
        if row["type"] == "income":
            income = Decimal(str(row["total"]))
        else:
            expense = Decimal(str(row["total"]))
        tx_count += row["count"]

    net = income - expense
    savings_rate = float((net / income * 100)) if income > 0 else 0.0

    conn.close()
    return {
        "year": year,
        "month": month,
        "profile_id": profile_id,
        "total_income": income,
        "total_expense": expense,
        "net_savings": net,
        "savings_rate": round(savings_rate, 1),
        "transaction_count": tx_count
    }


def get_category_breakdown(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
    type_filter: TransactionType = TransactionType.EXPENSE
) -> List[Dict[str, Any]]:
    """Breakdown by category for charts."""
    conn = get_connection()
    cursor = conn.cursor()

    start, end = _month_bounds(year, month)

    query = f"""
        SELECT 
            c.id as category_id,
            c.name,
            c.icon,
            SUM(t.amount) as total,
            COUNT(*) as count
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.date >= ? AND t.date < ? AND t.type = ?{_TX_T_ACTIVE}
    """
    params: List[Any] = [start, end, type_filter.value]

    if profile_id is not None:
        query += " AND t.profile_id = ?"
        params.append(profile_id)

    query += " GROUP BY c.id ORDER BY total DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "category_id": r["category_id"],
            "name": r["name"],
            "icon": r["icon"] or "📦",
            "total": Decimal(str(r["total"])),
            "count": r["count"]
        }
        for r in rows
    ]


def get_category_breakdown_with_projections(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    type_filter: TransactionType = TransactionType.EXPENSE,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Actual category totals plus recurring items not yet logged in the month."""
    actual = get_category_breakdown(year, month, profile_id, type_filter)
    pending = _pending_recurring_for_month(
        year, month, profile_id, consolidated, type_filter=type_filter
    )
    if not pending:
        return actual, False

    by_category: Dict[int, Dict[str, Any]] = {
        item["category_id"]: dict(item) for item in actual
    }
    for template in pending:
        category_id = template["category_id"]
        amount = template["amount"]
        if category_id in by_category:
            by_category[category_id]["total"] += amount
            by_category[category_id]["count"] += 1
        else:
            by_category[category_id] = {
                "category_id": category_id,
                "name": template["name"],
                "icon": template["icon"],
                "total": amount,
                "count": 1,
            }

    merged = sorted(by_category.values(), key=lambda item: item["total"], reverse=True)
    return merged, True


def get_monthly_summary_with_projections(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
) -> Tuple[Dict[str, Any], bool]:
    summary = dict(get_monthly_summary(year, month, profile_id))
    pending = _pending_recurring_for_month(year, month, profile_id=profile_id, consolidated=False)
    if not pending:
        return summary, False

    extra_income = Decimal("0")
    extra_expense = Decimal("0")
    for template in pending:
        if template["type"] == TransactionType.INCOME.value:
            extra_income += template["amount"]
        else:
            extra_expense += template["amount"]

    income = summary["total_income"] + extra_income
    expense = summary["total_expense"] + extra_expense
    net = income - expense
    rate = float((net / income * 100)) if income > 0 else 0.0
    summary.update({
        "total_income": income,
        "total_expense": expense,
        "net_savings": net,
        "savings_rate": round(rate, 1),
        "transaction_count": summary["transaction_count"] + len(pending),
    })
    return summary, True


def get_consolidated_summary_with_projections(year: int, month: int) -> Tuple[Dict[str, Any], bool]:
    profiles = get_all_profiles()
    total_income = Decimal("0")
    total_expense = Decimal("0")
    total_count = 0
    projected = False

    for profile in profiles:
        summary, is_projected = get_monthly_summary_with_projections(year, month, profile.id)
        total_income += summary["total_income"]
        total_expense += summary["total_expense"]
        total_count += summary["transaction_count"]
        projected = projected or is_projected

    xfer = _transfer_totals_month(year, month)
    total_income -= xfer[0]
    total_expense -= xfer[1]
    net = total_income - total_expense
    rate = float((net / total_income * 100)) if total_income > 0 else 0.0
    return {
        "year": year,
        "month": month,
        "profile_id": None,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net,
        "savings_rate": round(rate, 1),
        "transaction_count": total_count,
        "profile_count": len(profiles),
    }, projected


def _transfer_totals_month(year: int, month: int) -> Tuple[Decimal, Decimal]:
    conn = get_connection()
    start, end = _month_bounds(year, month)
    rows = conn.execute(
        f"""
        SELECT type, SUM(amount) AS total FROM transactions t
        JOIN profiles p ON t.profile_id = p.id AND p.is_active = 1
        WHERE t.date >= ? AND t.date < ? AND IFNULL(t.notes, '') LIKE 'transfer:%'
        GROUP BY type
        """,
        (start, end),
    ).fetchall()
    conn.close()
    income = expense = Decimal("0")
    for row in rows:
        if row["type"] == "income":
            income = Decimal(str(row["total"] or 0))
        else:
            expense = Decimal(str(row["total"] or 0))
    return income, expense


def get_balance_evolution(
    months_back: int = 6,
    profile_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get month-by-month net savings and cumulative balance for line chart."""
    conn = get_connection()
    cursor = conn.cursor()

    # Get last N months dynamically
    today = date.today()
    results = []

    cumulative = Decimal("0")

    for i in range(months_back - 1, -1, -1):
        target_date = today.replace(day=1)
        # Go back i months
        for _ in range(i):
            if target_date.month == 1:
                target_date = target_date.replace(year=target_date.year - 1, month=12)
            else:
                target_date = target_date.replace(month=target_date.month - 1)

        year = target_date.year
        month = target_date.month

        summary = get_monthly_summary(year, month, profile_id)
        cumulative += summary["net_savings"]

        results.append({
            "year": year,
            "month": month,
            "label": format_month_year_label(year, month),
            "net_savings": summary["net_savings"],
            "cumulative_balance": cumulative,
            "income": summary["total_income"],
            "expense": summary["total_expense"]
        })

    conn.close()
    return results


def get_consolidated_summary(year: int, month: int) -> Dict[str, Any]:
    """Sum of all active profiles for the month (excludes internal transfers)."""
    conn = get_connection()
    start, end = _month_bounds(year, month)
    rows = conn.execute(
        f"""
        SELECT t.type, SUM(t.amount) AS total, COUNT(*) AS count
        FROM transactions t
        JOIN profiles p ON t.profile_id = p.id AND p.is_active = 1
        WHERE t.date >= ? AND t.date < ?{_TRANSFER_EXCLUDE}{_TX_T_ACTIVE}
        GROUP BY t.type
        """,
        (start, end),
    ).fetchall()
    conn.close()

    income = expense = Decimal("0")
    tx_count = 0
    for row in rows:
        if row["type"] == "income":
            income = Decimal(str(row["total"] or 0))
        else:
            expense = Decimal(str(row["total"] or 0))
        tx_count += row["count"] or 0

    net = income - expense
    rate = float((net / income * 100)) if income > 0 else 0.0
    profiles = get_all_profiles()
    return {
        "year": year,
        "month": month,
        "profile_id": None,
        "total_income": income,
        "total_expense": expense,
        "net_savings": net,
        "savings_rate": round(rate, 1),
        "transaction_count": tx_count,
        "profile_count": len(profiles),
    }


def get_ytd_totals(
    year: int,
    up_to_month: int,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> Dict[str, Any]:
    """Single-query YTD aggregation (replaces monthly loop)."""
    conn = get_connection()
    cursor = conn.cursor()

    start = f"{year}-01-01"
    if up_to_month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{up_to_month + 1:02d}-01"

    if consolidated:
        query = f"""
            SELECT t.type, SUM(t.amount) as total, COUNT(*) as count
            FROM transactions t
            JOIN profiles p ON t.profile_id = p.id
            WHERE t.date >= ? AND t.date < ?
              AND p.is_active = 1{_TRANSFER_EXCLUDE}{_TX_T_ACTIVE}
            GROUP BY t.type
        """
        params: List[Any] = [start, end]
    else:
        query = f"""
            SELECT type, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE date >= ? AND date < ?{_TX_ACTIVE}
        """
        params = [start, end]
        if profile_id is not None:
            query += " AND profile_id = ?"
            params.append(profile_id)
        query += " GROUP BY type"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    income = Decimal("0")
    expense = Decimal("0")
    tx_count = 0
    for row in rows:
        if row["type"] == "income":
            income = Decimal(str(row["total"] or 0))
        else:
            expense = Decimal(str(row["total"] or 0))
        tx_count += row["count"] or 0

    net = income - expense
    rate = float((net / income * 100)) if income > 0 else 0.0
    return {
        "year": year,
        "total_income": income,
        "total_expense": expense,
        "net_savings": net,
        "savings_rate": round(rate, 1),
        "transaction_count": tx_count,
    }