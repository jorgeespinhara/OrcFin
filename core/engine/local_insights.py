"""Offline finance insights from seasonal data and budgets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.db.repositories.budgets import get_budgets_for_month, get_consolidated_budgets_for_month
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights


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
            tips.append(
                f"Despesas em {hit['label']} estão {pct:.0f}% acima da média dos últimos anos."
            )
        elif pct is not None and pct < -15:
            tips.append(f"Despesas em {hit['label']} estão abaixo do habitual ({pct:.0f}%).")

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
            tips.append(f"Orçamento estourado: {b['category_name']}.")
        elif pct >= 85:
            tips.append(f"Orçamento de {b['category_name']} em {pct:.0f}% do limite.")

    if not tips:
        tips.append("Nenhum alerta local neste período — continue acompanhando receitas e despesas.")

    return tips[:limit]