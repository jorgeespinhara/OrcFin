"""Local insight when AI providers are unavailable."""

from __future__ import annotations

from core.domain.value_objects.money import format_brl
from core.models import AIInsight


def build_local_fallback_insight(
    profile_id: int | None = None,
    consolidated: bool = True,
) -> AIInsight:
    from datetime import datetime

    from core.engine.reporting import get_current_month_summary, get_year_to_date_summary

    current = get_current_month_summary(profile_id, consolidated)
    ytd = get_year_to_date_summary(profile_id, consolidated)

    income = current["total_income"]
    expense = current["total_expense"]
    net = current["net_savings"]
    rate = current["savings_rate"]

    summary = (
        f"No mês atual, receitas de {format_brl(income)} e despesas de {format_brl(expense)}, "
        f"com economia líquida de {format_brl(net)} (taxa de poupança: {rate}%)."
    )

    tips: list[str] = []
    if rate < 10:
        tips.append(
            "Taxa de poupança abaixo de 10%. Revise as categorias de despesa com maior volume."
        )
    if expense > income:
        tips.append(
            "Despesas superaram receitas neste período. Priorize cortes em gastos não essenciais."
        )
    if ytd["savings_rate"] < rate:
        tips.append(
            "A tendência YTD está pior que o mês atual. Evite novos compromissos fixos."
        )

    return AIInsight(
        provider="Análise local (offline)",
        model="finance-engine",
        summary=summary,
        predictions=[
            f"Economia acumulada no ano: {format_brl(ytd['net_savings'])} "
            f"(taxa YTD: {ytd['savings_rate']}%)."
        ],
        cost_reduction_tips=tips or [
            "Mantenha lançamentos em dia para interpretações mais precisas."
        ],
        general_advice=(
            "Esta análise foi gerada localmente pelo motor financeiro do OrcFin porque a API "
            "de IA não respondeu. Os números vêm do motor financeiro local; a IA só "
            "interpreta quando disponível."
        ),
        generated_at=datetime.now(),
    )