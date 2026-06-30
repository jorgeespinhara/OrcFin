"""How much can still be spent this month — local planning, no AI."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from core.db.queries import get_consolidated_summary, get_monthly_summary
from core.db.repositories.budgets import get_budgets_for_month, get_consolidated_budgets_for_month
from core.engine.recurrence_detection import detect_recurring_transactions


def get_spendable_amount(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    year: int | None = None,
    month: int | None = None,
    safety_pct: float = 10.0,
) -> Dict[str, Any]:
    from datetime import date

    today = date.today()
    y, m = year or today.year, month or today.month

    if consolidated:
        summary = get_consolidated_summary(y, m)
        budgets = get_consolidated_budgets_for_month(y, m)
    else:
        summary = get_monthly_summary(y, m, profile_id)
        budgets = get_budgets_for_month(y, m, profile_id)

    income = Decimal(str(summary["total_income"]))
    expense = Decimal(str(summary["total_expense"]))

    recurring = sum(
        Decimal(str(r.get("average_amount") or 0))
        for r in detect_recurring_transactions(profile_id, consolidated)
        if r.get("type") == "expense"
    )
    budget_room = sum(
        max(Decimal("0"), Decimal(str(b["limit"])) - Decimal(str(b["spent"])))
        for b in budgets
    )
    margin = (income * Decimal(str(safety_pct)) / 100).quantize(Decimal("0.01"))

    spendable = income - expense - recurring - margin
    spendable = max(Decimal("0"), spendable)

    return {
        "year": y,
        "month": m,
        "income": income,
        "expense_so_far": expense,
        "recurring_fixed": recurring,
        "safety_margin": margin,
        "budget_headroom": budget_room,
        "spendable": spendable,
        "safety_pct": safety_pct,
    }