"""Decision cards for the dashboard — composes existing local engines."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

from core.db.queries import get_consolidated_summary, get_monthly_summary
from core.db.repositories.dismissed_insights import dismissed_keys
from core.db.repositories.mei import get_mei_profiles

from core.domain.value_objects.money import format_brl
from core.engine.due_dates import get_upcoming_due_dates
from core.engine.local_insights import get_local_finance_insights
from core.engine.spendable import get_spendable_amount
from core.mei import get_revenue_limit_status
from core.mei_receivables import get_receivables_aging
from core.services.mei_service import das_payment_exists


def _prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _summary(profile_id: int | None, consolidated: bool, year: int, month: int) -> dict:
    if consolidated:
        return get_consolidated_summary(year, month)
    return get_monthly_summary(year, month, profile_id)


def _card(
    *,
    key: str,
    severity: str,
    message: str,
    hint: str = "",
    action: str | None = None,
    action_label: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "severity": severity,
        "message": message,
        "hint": hint,
        "action": action,
        "action_label": action_label or "Ver",
    }


def _mei_cards(profile_id: int | None, year: int, month: int) -> list[dict[str, Any]]:
    if not profile_id:
        return []
    mei_ids = {p.id for p in get_mei_profiles()}
    if profile_id not in mei_ids:
        return []
    cards: list[dict[str, Any]] = []
    limit = get_revenue_limit_status(profile_id)
    pct = float(limit.get("usage_percent") or 0)
    if pct >= 70:
        cards.append(_card(
            key=f"mei_limit_{year}",
            severity="critical" if pct >= 90 else "warning",
            message=f"Faturamento MEI em {pct:.0f}% do limite anual.",
            hint=f"YTD {format_brl(limit.get('ytd_revenue', 0))}",
            action="mei_home",
            action_label="Ver MEI",
        ))
    if not das_payment_exists(profile_id, year, month):
        cards.append(_card(
            key=f"mei_das_{year}_{month}",
            severity="warning",
            message="DAS do mês ainda não registrado como pago.",
            hint=f"{month:02d}/{year}",
            action="mei_obrigacoes",
            action_label="Obrigações",
        ))
    aging = get_receivables_aging(profile_id)
    overdue = sum(
        Decimal(str(aging.get("totals", {}).get(k) or 0))
        for k in ("1_30", "31_60", "61_90", "90_plus")
    )
    overdue_count = sum(len(aging.get("buckets", {}).get(k) or []) for k in ("1_30", "31_60", "61_90", "90_plus"))
    if overdue > 0:
        cards.append(_card(
            key=f"mei_receivables_{year}_{month}",
            severity="warning",
            message=f"Recebíveis MEI em atraso: {format_brl(overdue)}.",
            hint=f"{overdue_count} nota(s)",
            action="mei_vendas",
            action_label="Vendas",
        ))
    return cards


def get_decision_cards(
    *,
    profile_id: int | None = None,
    consolidated: bool = False,
    year: int | None = None,
    month: int | None = None,
    limit: int = 8,
    include_dismissed: bool = False,
) -> list[dict[str, Any]]:
    today = date.today()
    y, m = year or today.year, month or today.month
    skip = set() if include_dismissed else dismissed_keys(profile_id)
    cards: list[dict[str, Any]] = []

    spend = get_spendable_amount(profile_id=profile_id, consolidated=consolidated, year=y, month=m)
    days_left = monthrange(y, m)[1] - today.day + 1 if y == today.year and m == today.month else monthrange(y, m)[1]
    daily = (spend["spendable"] / days_left).quantize(Decimal("0.01")) if days_left > 0 else Decimal("0")
    key_spend = f"spendable_{y}_{m}"
    if key_spend not in skip:
        if spend["spendable"] > 0:
            cards.append(_card(
                key=key_spend,
                severity="success",
                message=f"Você pode gastar cerca de {format_brl(daily)} por dia até o fim do mês.",
                hint=f"Total disponível: {format_brl(spend['spendable'])}",
                action="budgets",
                action_label="Orçamentos",
            ))
        else:
            cards.append(_card(
                key=key_spend,
                severity="warning",
                message="Margem apertada neste mês. Revise despesas fixas e orçamentos.",
                hint=f"Receitas {format_brl(spend['income'])} · Despesas {format_brl(spend['expense_so_far'])}",
                action="transactions",
                action_label="Lançamentos",
            ))

    dues = get_upcoming_due_dates(profile_id, consolidated, days_ahead=15)
    due_total = sum(Decimal(str(d.get("amount") or 0)) for d in dues)
    key_due = f"due_dates_{y}_{m}"
    if dues and key_due not in skip:
        cards.append(_card(
            key=key_due,
            severity="warning" if len(dues) >= 3 else "info",
            message=f"{len(dues)} vencimento(s) nos próximos 15 dias"
            + (f" ({format_brl(due_total)})." if due_total > 0 else "."),
            hint=dues[0]["label"] if dues else "",
            action="transactions",
            action_label="Ver vencimentos",
        ))

    cur = _summary(profile_id, consolidated, y, m)
    py, pm = _prev_month(y, m)
    prev = _summary(profile_id, consolidated, py, pm)
    exp_pct = float(
        (Decimal(str(cur["total_expense"])) - Decimal(str(prev["total_expense"])))
        / Decimal(str(prev["total_expense"])) * 100
    ) if prev["total_expense"] else 0
    key_trend = f"expense_trend_{y}_{m}"
    if abs(exp_pct) >= 10 and key_trend not in skip:
        direction = "subiram" if exp_pct > 0 else "caíram"
        cards.append(_card(
            key=key_trend,
            severity="warning" if exp_pct > 15 else "info",
            message=f"Despesas {direction} {abs(exp_pct):.0f}% em relação ao mês anterior.",
            hint=f"{format_brl(cur['total_expense'])} vs {format_brl(prev['total_expense'])}",
            action="reports",
            action_label="Relatórios",
        ))

    for i, tip in enumerate(get_local_finance_insights(profile_id, consolidated, y, m, limit=4)):
        key = f"insight_{y}_{m}_{i}"
        if key in skip:
            continue
        low = tip.lower()
        if "estourado" in low or "estourad" in low:
            sev = "critical"
        elif "85%" in tip or "acima" in low:
            sev = "warning"
        else:
            sev = "info"
        cards.append(_card(
            key=key,
            severity=sev,
            message=tip,
            action="budgets",
            action_label="Orçamentos",
        ))

    if not consolidated:
        for mc in _mei_cards(profile_id, y, m):
            if mc["key"] not in skip:
                cards.append(mc)

    return cards[:limit]