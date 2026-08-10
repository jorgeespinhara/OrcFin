"""Offline finance insights from seasonal data and budgets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.db.repositories.budgets import get_budgets_for_month, get_consolidated_budgets_for_month
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights
from core.i18n import t


def get_local_finance_insights(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    year: int | None = None,
    month: int | None = None,
    limit: int = 5,
) -> List[str]:
    from datetime import date

    today = date.today()
    y, m = year or today.year, month or today.month
    tips: List[str] = []

    seasonal = get_seasonal_expense_comparison(
        profile_id=profile_id,
        consolidated=consolidated,
        reference_year=y,
        years_back=3,
    )
    for hit in get_seasonal_highlights(seasonal, top_n=3):
        if hit["month"] != m:
            continue
        pct = hit.get("vs_average_pct")
        if pct is not None and pct > 10:
            tips.append(t("insight.seasonal_high", label=hit["label"], pct=f"{pct:.0f}"))
        elif pct is not None and pct < -15:
            tips.append(t("insight.seasonal_low", label=hit["label"], pct=f"{pct:.0f}"))

    budgets = (
        get_consolidated_budgets_for_month(y, m)
        if consolidated
        else get_budgets_for_month(y, m, profile_id)
    )
    for b in budgets:
        if b["limit"] <= 0:
            continue
        pct = float(b["spent"] / b["limit"] * 100) if b["limit"] else 0
        if pct >= 100:
            tips.append(t("insight.budget_over", name=b["category_name"]))
        elif pct >= 85:
            tips.append(t("insight.budget_near", name=b["category_name"], pct=f"{pct:.0f}"))

    if not tips:
        tips.append(t("insight.none"))

    return tips[:limit]