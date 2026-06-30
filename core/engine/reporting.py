"""Finance engine — summaries, projections, trends, and AI context building."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from core.db.queries import (
    get_balance_evolution,
    get_category_breakdown,
    get_category_breakdown_with_projections,
    get_consolidated_summary,
    get_consolidated_summary_with_projections,
    get_monthly_summary,
    get_monthly_summary_with_projections,
    get_ytd_totals,
)
from core.db.repositories.budgets import (
    get_budgets_for_month,
    get_consolidated_budgets_for_month,
)
from core.db.repositories.categories import get_all_categories
from core.domain.month_format import format_month_year_label
from core.domain.value_objects.money import format_brl
from core.models import TransactionType


def get_current_month_summary(profile_id: Optional[int] = None, consolidated: bool = False) -> Dict[str, Any]:
    """Get summary for the current month. Supports consolidated view."""
    today = date.today()
    if consolidated:
        return get_consolidated_summary(today.year, today.month)
    return get_monthly_summary(today.year, today.month, profile_id)


def get_previous_month_comparison(
    profile_id: Optional[int] = None,
    consolidated: bool = False
) -> Dict[str, Any]:
    """Compare current month vs previous month (good for trends)."""
    today = date.today()
    current = get_current_month_summary(profile_id, consolidated)

    # Previous month
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1

    if consolidated:
        previous = get_consolidated_summary(prev_year, prev_month)
    else:
        previous = get_monthly_summary(prev_year, prev_month, profile_id)

    income_change = current["total_income"] - previous["total_income"]
    expense_change = current["total_expense"] - previous["total_expense"]
    net_change = current["net_savings"] - previous["net_savings"]

    return {
        "current": current,
        "previous": previous,
        "income_change": income_change,
        "expense_change": expense_change,
        "net_change": net_change,
        "income_change_pct": _safe_pct_change(previous["total_income"], current["total_income"]),
        "expense_change_pct": _safe_pct_change(previous["total_expense"], current["total_expense"]),
    }


def _safe_pct_change(old: Decimal, new: Decimal) -> float:
    if old == 0:
        return 100.0 if new > 0 else 0.0
    return float(((new - old) / old) * 100)


def _shift_month(year: int, month: int, offset: int) -> Tuple[int, int]:
    """Return (year, month) offset months from anchor (offset may be negative)."""
    total = year * 12 + (month - 1) + offset
    return total // 12, total % 12 + 1


def _resolve_dashboard_period(
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Tuple[int, Optional[int], str]:
    """Return effective year, optional month, and period label key."""
    today = date.today()
    target_year = year or today.year
    if month is not None:
        return target_year, month, "month"
    if target_year == today.year:
        return target_year, today.month, "ytd"
    return target_year, None, "year"


def _summary_for_period(
    year: int,
    month: Optional[int],
    profile_id: Optional[int],
    consolidated: bool,
) -> Dict[str, Any]:
    if month is not None:
        if consolidated:
            summary, _ = get_consolidated_summary_with_projections(year, month)
            return summary
        summary, _ = get_monthly_summary_with_projections(year, month, profile_id)
        return summary

    if year == date.today().year:
        return get_year_to_date_summary(profile_id, consolidated, year=year)
    income = Decimal("0")
    expense = Decimal("0")
    count = 0
    for m in range(1, 13):
        if consolidated:
            s = get_consolidated_summary(year, m)
        else:
            s = get_monthly_summary(year, m, profile_id)
        income += s["total_income"]
        expense += s["total_expense"]
        count += s["transaction_count"]
    net = income - expense
    rate = float((net / income * 100)) if income > 0 else 0.0
    return {
        "year": year,
        "month": None,
        "profile_id": profile_id,
        "total_income": income,
        "total_expense": expense,
        "net_savings": net,
        "savings_rate": round(rate, 1),
        "transaction_count": count,
    }


def _comparison_for_period(
    year: int,
    month: Optional[int],
    profile_id: Optional[int],
    consolidated: bool,
) -> Dict[str, Any]:
    current = _summary_for_period(year, month, profile_id, consolidated)
    if month is not None:
        prev_year, prev_month = _shift_month(year, month, -1)
        if consolidated:
            previous = get_consolidated_summary(prev_year, prev_month)
        else:
            previous = get_monthly_summary(prev_year, prev_month, profile_id)
    elif year == date.today().year:
        if date.today().month <= 1:
            previous = {
                "total_income": Decimal("0"),
                "total_expense": Decimal("0"),
                "net_savings": Decimal("0"),
            }
        else:
            previous = get_year_to_date_summary(
                profile_id, consolidated, year=year, up_to_month=date.today().month - 1
            )
    else:
        prev_income = Decimal("0")
        prev_expense = Decimal("0")
        for m in range(1, 13):
            if consolidated:
                s = get_consolidated_summary(year - 1, m)
            else:
                s = get_monthly_summary(year - 1, m, profile_id)
            prev_income += s["total_income"]
            prev_expense += s["total_expense"]
        previous = {
            "total_income": prev_income,
            "total_expense": prev_expense,
            "net_savings": prev_income - prev_expense,
        }

    return {
        "current": current,
        "previous": previous,
        "income_change": current["total_income"] - previous["total_income"],
        "expense_change": current["total_expense"] - previous["total_expense"],
        "net_change": current["net_savings"] - previous["net_savings"],
        "income_change_pct": _safe_pct_change(previous["total_income"], current["total_income"]),
        "expense_change_pct": _safe_pct_change(previous["total_expense"], current["total_expense"]),
    }


def get_balance_evolution_anchored(
    months_back: int = 12,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> List[Dict[str, Any]]:
    """Month-by-month evolution ending at the given period (defaults to today)."""
    today = date.today()
    anchor_year = end_year or today.year
    anchor_month = end_month or today.month

    results = []
    cumulative = Decimal("0")
    for offset in range(-(months_back - 1), 1):
        y, m = _shift_month(anchor_year, anchor_month, offset)
        if consolidated:
            summary, _ = get_consolidated_summary_with_projections(y, m)
        else:
            summary, _ = get_monthly_summary_with_projections(y, m, profile_id)
        cumulative += summary["net_savings"]
        results.append({
            "year": y,
            "month": m,
            "label": format_month_year_label(y, m),
            "net_savings": summary["net_savings"],
            "cumulative_balance": cumulative,
            "income": summary["total_income"],
            "expense": summary["total_expense"],
        })
    return results


def get_monthly_income_expense_series(
    months_back: int = 12,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> List[Dict[str, Any]]:
    """Monthly income and expense for bar charts."""
    evolution = get_balance_evolution_anchored(
        months_back=months_back,
        end_year=end_year,
        end_month=end_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )
    return [
        {
            "year": p["year"],
            "month": p["month"],
            "label": p["label"],
            "income": p["income"],
            "expense": p["expense"],
            "net_savings": p["net_savings"],
        }
        for p in evolution
    ]


def get_category_monthly_trend(
    category_id: int,
    months_back: int = 6,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> List[Dict[str, Any]]:
    """Expense trend for a single category across months."""
    today = date.today()
    anchor_year = end_year or today.year
    anchor_month = end_month or today.month
    pid = None if consolidated else profile_id

    points = []
    for offset in range(-(months_back - 1), 1):
        y, m = _shift_month(anchor_year, anchor_month, offset)
        breakdown = get_category_breakdown(y, m, pid, TransactionType.EXPENSE)
        total = next((c["total"] for c in breakdown if c["category_id"] == category_id), Decimal("0"))
        points.append({"year": y, "month": m, "label": format_month_year_label(y, m), "total": total})
    return points


def get_budgets_for_dashboard(
    year: int,
    month: int,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> List[Dict[str, Any]]:
    if consolidated:
        return get_consolidated_budgets_for_month(year, month)
    if profile_id is None:
        return []
    return get_budgets_for_month(year, month, profile_id)


def build_projection_chart_points(
    evolution: List[Dict[str, Any]],
    months_ahead: int = 3,
) -> List[Dict[str, Any]]:
    """Turn projection data into labeled chart points continuing cumulative series."""
    if not evolution:
        return []

    projection = calculate_simple_projection(evolution, months_ahead=months_ahead)
    last = evolution[-1]
    anchor_year = last["year"]
    anchor_month = last["month"]
    points = []
    for item in projection.get("projections", []):
        offset = item["month_offset"]
        y, m = _shift_month(anchor_year, anchor_month, offset)
        points.append({
            "year": y,
            "month": m,
            "label": format_month_year_label(y, m),
            "month_offset": offset,
            "projected_net": item["projected_net"],
            "projected_cumulative": item["projected_cumulative"],
            "is_projected": True,
        })
    return points


def get_dashboard_data(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    year: Optional[int] = None,
    month: Optional[int] = None,
    projection_months_ahead: int = 3,
) -> Dict[str, Any]:
    """Main data package for the Dashboard view."""
    target_year, target_month, period_mode = _resolve_dashboard_period(year, month)
    pid = profile_id if not consolidated else None

    current = _summary_for_period(target_year, month, profile_id, consolidated)
    comparison = _comparison_for_period(target_year, month, profile_id, consolidated)

    cat_year = target_year
    category_breakdown_is_projected = False
    if month is not None:
        category_breakdown, category_breakdown_is_projected = get_category_breakdown_with_projections(
            cat_year,
            month,
            pid,
            consolidated=consolidated,
            type_filter=TransactionType.EXPENSE,
        )
    elif period_mode == "ytd":
        category_breakdown = []
        for m in range(1, (target_month or date.today().month) + 1):
            for cat in get_category_breakdown(cat_year, m, pid, TransactionType.EXPENSE):
                existing = next((c for c in category_breakdown if c["category_id"] == cat["category_id"]), None)
                if existing:
                    existing["total"] += cat["total"]
                    existing["count"] += cat["count"]
                else:
                    category_breakdown.append(dict(cat))
        category_breakdown.sort(key=lambda x: x["total"], reverse=True)
    else:
        category_breakdown = []
        for m in range(1, 13):
            for cat in get_category_breakdown(cat_year, m, pid, TransactionType.EXPENSE):
                existing = next((c for c in category_breakdown if c["category_id"] == cat["category_id"]), None)
                if existing:
                    existing["total"] += cat["total"]
                    existing["count"] += cat["count"]
                else:
                    category_breakdown.append(dict(cat))
        category_breakdown.sort(key=lambda x: x["total"], reverse=True)

    evolution = get_balance_evolution_anchored(
        months_back=12,
        end_year=target_year,
        end_month=month or target_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )
    months_ahead = max(1, min(12, projection_months_ahead))
    projection_detail = build_forward_projection(
        profile_id=profile_id,
        consolidated=consolidated,
        end_year=target_year,
        end_month=month or target_month,
        months_ahead=months_ahead,
    )
    projection = calculate_simple_projection(evolution, months_ahead=months_ahead)
    projection.update({
        "projected_in_3_months": projection_detail["projected_net_total"],
        "projected_income_total": projection_detail["projected_income_total"],
        "projected_expense_total": projection_detail["projected_expense_total"],
        "projected_net_total": projection_detail["projected_net_total"],
        "average_monthly_income": projection_detail["average_monthly_income"],
        "average_monthly_expense": projection_detail["average_monthly_expense"],
    })
    projection_chart = projection_detail["monthly_points"]

    budget_month = month or (target_month if period_mode == "ytd" else 12)
    budgets = get_budgets_for_dashboard(
        target_year,
        budget_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )

    return {
        "current_month": current,
        "comparison": comparison,
        "category_breakdown": category_breakdown,
        "category_breakdown_is_projected": category_breakdown_is_projected,
        "balance_evolution": evolution,
        "projection": projection,
        "projection_detail": projection_detail,
        "projection_chart": projection_chart,
        "monthly_series": get_monthly_income_expense_series(
            months_back=12,
            end_year=target_year,
            end_month=month or target_month,
            profile_id=profile_id,
            consolidated=consolidated,
        ),
        "is_consolidated": consolidated,
        "profile_id": profile_id,
        "period_year": target_year,
        "period_month": month,
        "period_mode": period_mode,
        "budgets": budgets,
        "budget_month": budget_month,
    }


def calculate_simple_projection(
    evolution: List[Dict[str, Any]],
    months_ahead: int = 3
) -> Dict[str, Any]:
    """Forward projection using average monthly net savings.

    ``projected_in_3_months`` is the expected net impact over the *next*
    ``months_ahead`` months (avg × N), not the cumulative balance including
    prior months — that lives in ``projected_cumulative_at_horizon``.
    """
    if not evolution:
        return {
            "projected_balance": Decimal("0"),
            "projected_in_3_months": Decimal("0"),
            "projected_cumulative_at_horizon": Decimal("0"),
            "scenarios": [],
        }

    nets = [e["net_savings"] for e in evolution if e["net_savings"] != 0]
    avg_net = sum(nets) / len(nets) if nets else Decimal("0")

    last_cumulative = evolution[-1]["cumulative_balance"]
    forward_total = avg_net * months_ahead

    projections = []
    cumulative = last_cumulative
    for m in range(1, months_ahead + 1):
        cumulative += avg_net
        projections.append({
            "month_offset": m,
            "projected_net": avg_net,
            "projected_cumulative": cumulative
        })

    return {
        "average_monthly_net": avg_net,
        "current_cumulative": last_cumulative,
        "projected_in_3_months": forward_total,
        "projected_cumulative_at_horizon": cumulative,
        "projections": projections
    }


def build_forward_projection(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    months_ahead: int = 3,
    history_months: int = 6,
) -> Dict[str, Any]:
    """Explicit income/expense/net forecast for the next N months."""
    today = date.today()
    anchor_year = end_year or today.year
    anchor_month = end_month or today.month

    evolution = get_balance_evolution_anchored(
        months_back=history_months,
        end_year=anchor_year,
        end_month=anchor_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )

    active = [e for e in evolution if e["income"] != 0 or e["expense"] != 0]
    if active:
        avg_income = sum(e["income"] for e in active) / len(active)
        avg_expense = sum(e["expense"] for e in active) / len(active)
        avg_net = sum(e["net_savings"] for e in active) / len(active)
    else:
        avg_income = avg_expense = avg_net = Decimal("0")

    monthly_points: List[Dict[str, Any]] = []
    total_income = Decimal("0")
    total_expense = Decimal("0")
    uses_average = False
    uses_recurring = False

    for offset in range(1, months_ahead + 1):
        y, m = _shift_month(anchor_year, anchor_month, offset)
        if consolidated:
            summary, projected = get_consolidated_summary_with_projections(y, m)
        else:
            summary, projected = get_monthly_summary_with_projections(y, m, profile_id)

        income = summary["total_income"]
        expense = summary["total_expense"]
        if projected:
            uses_recurring = True
        if income == 0 and expense == 0 and active:
            income = avg_income
            expense = avg_expense
            uses_average = True

        net = income - expense
        total_income += income
        total_expense += expense
        monthly_points.append({
            "year": y,
            "month": m,
            "label": format_month_year_label(y, m),
            "income": income,
            "expense": expense,
            "net_savings": net,
            "is_projected": True,
        })

    total_net = total_income - total_expense
    basis_parts = []
    if active:
        basis_parts.append(f"média de {len(active)} mês(es) com movimentação")
    if uses_recurring:
        basis_parts.append("lançamentos recorrentes")
    if uses_average:
        basis_parts.append("extrapolação da média recente")
    basis_label = (
        "Estimativa com base em: " + ", ".join(basis_parts)
        if basis_parts
        else "Sem histórico suficiente — cadastre receitas e despesas"
    )

    return {
        "months_ahead": months_ahead,
        "average_monthly_income": avg_income,
        "average_monthly_expense": avg_expense,
        "average_monthly_net": avg_net,
        "projected_income_total": total_income,
        "projected_expense_total": total_expense,
        "projected_net_total": total_net,
        "projected_in_3_months": total_net,
        "monthly_points": monthly_points,
        "basis_label": basis_label,
        "has_history": bool(active),
    }


def get_top_expense_categories_with_trend(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
    months_back: int = 8,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """Expense categories that already have data, ranked by recent total."""
    today = date.today()
    anchor_year = end_year or today.year
    anchor_month = end_month or today.month

    ranked: List[Dict[str, Any]] = []
    for category in get_all_categories():
        if category.type != TransactionType.EXPENSE:
            continue
        trend = get_category_monthly_trend(
            category.id,
            months_back=months_back,
            end_year=anchor_year,
            end_month=anchor_month,
            profile_id=profile_id,
            consolidated=consolidated,
        )
        total = sum((p["total"] for p in trend), Decimal("0"))
        if total > 0:
            ranked.append({
                "category_id": category.id,
                "name": category.name,
                "icon": category.icon or "📦",
                "trend": trend,
                "total": total,
            })

    ranked.sort(key=lambda item: item["total"], reverse=True)
    return ranked[:limit]


def get_year_to_date_summary(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    year: Optional[int] = None,
    up_to_month: Optional[int] = None,
) -> Dict[str, Any]:
    """YTD totals (useful for reports)."""
    today = date.today()
    target_year = year or today.year
    if up_to_month is not None:
        last_month = up_to_month
    elif target_year == today.year:
        last_month = today.month
    else:
        last_month = 12

    return get_ytd_totals(
        year=target_year,
        up_to_month=last_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )


def generate_ai_context(
    profile_id: Optional[int] = None,
    consolidated: bool = True
) -> str:
    """
    Generate a privacy-safe, aggregated context string to send to AI.
    Never sends individual transactions, invoice/import data, card numbers,
    holder names, or merchant descriptions (LGPD).
    """
    from core.privacy import anonymize_profile_label

    today = date.today()
    current = get_current_month_summary(profile_id, consolidated)
    ytd = get_year_to_date_summary(profile_id, consolidated)
    evolution = get_balance_evolution(6, profile_id if not consolidated else None)

    # Category top 5 expenses this month (names only — no line-item descriptions)
    cat_breakdown = get_category_breakdown(
        today.year,
        today.month,
        profile_id if not consolidated else None,
        TransactionType.EXPENSE,
    )
    top_categories = sorted(cat_breakdown, key=lambda x: x["total"], reverse=True)[:5]

    profile_label = anonymize_profile_label(consolidated)

    context = f"""
Você é um consultor financeiro sênior especializado em finanças pessoais e familiares no Brasil.

CONTEXTO ATUAL (agregado e anônimo — sem dados de faturas importadas):
- Mês atual ({today.month:02d}/{today.year}): 
  Receita total: R$ {float(current['total_income']):,.2f}
  Despesa total: R$ {float(current['total_expense']):,.2f}
  Economia líquida: R$ {float(current['net_savings']):,.2f}
  Taxa de poupança: {current['savings_rate']}%

- Ano até agora (YTD):
  Receita: R$ {float(ytd['total_income']):,.2f}
  Despesa: R$ {float(ytd['total_expense']):,.2f}
  Economia: R$ {float(ytd['net_savings']):,.2f}
  Taxa de poupança YTD: {ytd['savings_rate']}%

- Evolução últimos 6 meses (saldo acumulado aproximado): 
  {[f"{e['label']}: R$ {float(e['cumulative_balance']):,.0f}" for e in evolution[-3:]]}

- Principais categorias de despesa do mês atual:
  {', '.join([f"{c['name']}: R$ {float(c['total']):,.0f}" for c in top_categories]) if top_categories else 'Sem dados suficientes'}

PERFIL: {profile_label}

TAREFA:
Forneça uma análise curta, objetiva e acionável em português brasileiro. Inclua:
1. Um resumo executivo de 2-3 frases.
2. Previsão realista para os próximos 3-6 meses (considerando a tendência atual).
3. 3-4 recomendações práticas e específicas para reduzir custos ou aumentar a taxa de poupança (priorize as categorias com maior impacto).
4. Uma sugestão de meta financeira simples e mensurável para os próximos 90 dias.

Responda de forma direta, sem enrolação, usando linguagem profissional mas acessível. Evite números genéricos — use os dados fornecidos.
"""
    return context.strip()