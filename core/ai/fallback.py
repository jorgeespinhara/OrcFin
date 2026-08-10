"""Local insight when AI providers are unavailable."""

from __future__ import annotations

from core.domain.value_objects.money import format_brl
from core.i18n import t
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

    summary = t(
        "ai.fallback_summary",
        income=format_brl(income),
        expense=format_brl(expense),
        net=format_brl(net),
        rate=rate,
    )

    tips: list[str] = []
    if rate < 10:
        tips.append(t("ai.tip_low_savings"))
    if expense > income:
        tips.append(t("ai.tip_expense_over_income"))
    if ytd["savings_rate"] < rate:
        tips.append(t("ai.tip_ytd_worse"))

    return AIInsight(
        provider=t("ai.provider_local"),
        model="finance-engine",
        summary=summary,
        predictions=[
            t(
                "ai.ytd_prediction",
                amount=format_brl(ytd["net_savings"]),
                rate=ytd["savings_rate"],
            )
        ],
        cost_reduction_tips=tips or [t("ai.tip_keep_current")],
        general_advice=t("ai.fallback_advice"),
        generated_at=datetime.now(),
    )
