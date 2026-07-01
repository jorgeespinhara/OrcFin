"""Decision cards for the dashboard — composes existing local engines."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

from core.db.queries import get_consolidated_summary, get_monthly_summary
from core.domain.value_objects.money import format_brl
from core.engine.due_dates import get_upcoming_due_dates
from core.engine.local_insights import get_local_finance_insights
from core.engine.spendable import get_spendable_amount


def _prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _summary(profile_id: int | None, consolidated: bool, year: int, month: int) -> dict:
    if consolidated:
        return get_consolidated_summary(year, month)
    return get_monthly_summary(year, month, profile_id)


def get_decision_cards(
    *,
    profile_id: int | None = None,
    consolidated: bool = False,
    year: int | None = None,
    month: int | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    today = date.today()
    y, m = year or today.year, month or today.month
    cards: list[dict[str, Any]] = []

    spend = get_spendable_amount(profile_id=profile_id, consolidated=consolidated, year=y, month=m)
    days_left = monthrange(y, m)[1] - today.day + 1 if y == today.year and m == today.month else monthrange(y, m)[1]
    daily = (spend["spendable"] / days_left).quantize(Decimal("0.01")) if days_left > 0 else Decimal("0")
    if spend["spendable"] > 0:
        cards.append({
            "id": "spendable",
            "severity": "success",
            "message": f"Você pode gastar cerca de {format_brl(daily)} por dia até o fim do mês.",
            "hint": f"Total disponível: {format_brl(spend['spendable'])}",
        })
    else:
        cards.append({
            "id": "spendable",
            "severity": "warning",
            "message": "Margem apertada neste mês. Revise despesas fixas e orçamentos.",
            "hint": f"Receitas {format_brl(spend['income'])} · Despesas {format_brl(spend['expense_so_far'])}",
        })

    dues = get_upcoming_due_dates(profile_id, consolidated, days_ahead=15)
    due_total = sum(Decimal(str(d.get("amount") or 0)) for d in dues)
    if dues:
        cards.append({
            "id": "due_dates",
            "severity": "warning" if len(dues) >= 3 else "info",
            "message": f"{len(dues)} vencimento(s) nos próximos 15 dias"
            + (f" ({format_brl(due_total)})." if due_total > 0 else "."),
            "hint": dues[0]["label"] if dues else "",
        })

    cur = _summary(profile_id, consolidated, y, m)
    py, pm = _prev_month(y, m)
    prev = _summary(profile_id, consolidated, py, pm)
    exp_pct = float(
        (Decimal(str(cur["total_expense"])) - Decimal(str(prev["total_expense"])))
        / Decimal(str(prev["total_expense"])) * 100
    ) if prev["total_expense"] else 0
    if abs(exp_pct) >= 10:
        direction = "subiram" if exp_pct > 0 else "caíram"
        cards.append({
            "id": "expense_trend",
            "severity": "warning" if exp_pct > 15 else "info",
            "message": f"Despesas {direction} {abs(exp_pct):.0f}% em relação ao mês anterior.",
            "hint": f"{format_brl(cur['total_expense'])} vs {format_brl(prev['total_expense'])}",
        })

    for tip in get_local_finance_insights(profile_id, consolidated, y, m, limit=4):
        low = tip.lower()
        if "estourado" in low or "estourad" in low:
            sev = "critical"
        elif "85%" in tip or "acima" in low:
            sev = "warning"
        else:
            sev = "info"
        cards.append({"id": "insight", "severity": sev, "message": tip, "hint": ""})

    return cards[:limit]