"""Seasonal expense comparison — same calendar month across years."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection

MONTH_LABELS = [
    "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def get_seasonal_expense_comparison(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    category_id: Optional[int] = None,
    reference_year: Optional[int] = None,
    years_back: int = 3,
) -> Dict[str, Any]:
    """Compare expenses by calendar month across multiple years."""
    ref_year = reference_year or date.today().year
    start_year = ref_year - years_back + 1

    conn = get_connection()
    query = """
        SELECT
            CAST(strftime('%m', t.date) AS INTEGER) AS month_num,
            CAST(strftime('%Y', t.date) AS INTEGER) AS year,
            SUM(t.amount) AS total
        FROM transactions t
    """
    params: List[Any] = []

    if consolidated:
        query += " JOIN profiles p ON t.profile_id = p.id AND p.is_active = 1"

    query += " WHERE t.type = 'expense'"
    query += " AND CAST(strftime('%Y', t.date) AS INTEGER) >= ?"
    query += " AND CAST(strftime('%Y', t.date) AS INTEGER) <= ?"
    params.extend([start_year, ref_year])

    if not consolidated and profile_id is not None:
        query += " AND t.profile_id = ?"
        params.append(profile_id)

    if category_id is not None:
        query += " AND t.category_id = ?"
        params.append(category_id)

    query += " GROUP BY month_num, year ORDER BY month_num, year"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    years = list(range(start_year, ref_year + 1))
    by_month: Dict[int, Dict[int, Decimal]] = {m: {} for m in range(1, 13)}
    for row in rows:
        by_month[row["month_num"]][row["year"]] = Decimal(str(row["total"] or 0))

    months_data = []
    for month in range(1, 13):
        year_totals = {y: by_month[month].get(y, Decimal("0")) for y in years}
        values = [float(year_totals[y]) for y in years if year_totals[y] > 0]
        avg = sum(values) / len(values) if values else 0.0
        ref_total = float(year_totals.get(ref_year, Decimal("0")))
        prev_year = ref_year - 1
        prev_total = float(year_totals.get(prev_year, Decimal("0")))
        yoy_pct = _pct_change(prev_total, ref_total) if prev_year in years else None
        vs_avg_pct = _pct_change(avg, ref_total) if avg > 0 else None

        months_data.append({
            "month": month,
            "label": MONTH_LABELS[month],
            "year_totals": year_totals,
            "reference_total": year_totals.get(ref_year, Decimal("0")),
            "average": Decimal(str(round(avg, 2))),
            "yoy_change_pct": yoy_pct,
            "vs_average_pct": vs_avg_pct,
        })

    return {
        "reference_year": ref_year,
        "years": years,
        "months": months_data,
        "category_id": category_id,
    }


def get_seasonal_highlights(data: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """Months with largest deviation from multi-year average in reference year."""
    scored = []
    for m in data["months"]:
        ref = float(m["reference_total"])
        avg = float(m["average"])
        if ref <= 0 and avg <= 0:
            continue
        deviation = abs(ref - avg)
        scored.append({
            "month": m["month"],
            "label": m["label"],
            "reference_total": m["reference_total"],
            "average": m["average"],
            "deviation": Decimal(str(round(deviation, 2))),
            "vs_average_pct": m["vs_average_pct"],
        })
    scored.sort(key=lambda x: float(x["deviation"]), reverse=True)
    return scored[:top_n]


def _pct_change(old: float, new: float) -> Optional[float]:
    if old == 0:
        return 100.0 if new > 0 else 0.0
    return round(((new - old) / old) * 100, 1)