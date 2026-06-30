"""Budget impact checks when creating expenses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from core.domain.value_objects.money import format_brl
from core.db.repositories.budgets import get_budgets_for_month
from core.models import TransactionType


def check_budget_impact(
    profile_id: int,
    category_id: int,
    amount: Decimal,
    tx_date: date,
    tx_type: TransactionType,
) -> Optional[str]:
    """Return warning message if expense affects budget threshold."""
    if tx_type != TransactionType.EXPENSE:
        return None

    budgets = get_budgets_for_month(tx_date.year, tx_date.month, profile_id)
    for budget in budgets:
        if budget["category_id"] != category_id:
            continue
        limit = budget["limit"]
        if limit <= 0:
            continue
        new_spent = budget["spent"] + amount
        pct = float(new_spent / limit * 100)
        name = budget["category_name"]

        if new_spent > limit:
            over = new_spent - limit
            return (
                f"Orçamento excedido em {name}: "
                f"{format_brl(new_spent)} de {format_brl(limit)} "
                f"(+{format_brl(over)})"
            )
        if pct >= 80:
            return (
                f"Atenção — {name} atingirá {pct:.0f}% do orçamento "
                f"({format_brl(new_spent)} / {format_brl(limit)})"
            )
    return None


def check_import_budget_impacts(
    profile_id: int,
    lines: list,
) -> List[str]:
    """Aggregate budget warnings for a batch of import lines."""
    from collections import defaultdict

    totals: dict[int, Decimal] = defaultdict(Decimal)
    dates: dict[int, date] = {}
    for line in lines:
        if not line.selected or line.tx_type != TransactionType.EXPENSE:
            continue
        cat = line.suggested_category_id
        if not cat:
            continue
        totals[cat] += line.amount
        dates[cat] = line.date

    warnings: List[str] = []
    for cat_id, total in totals.items():
        msg = check_budget_impact(profile_id, cat_id, total, dates[cat_id], TransactionType.EXPENSE)
        if msg:
            warnings.append(msg)
    return warnings