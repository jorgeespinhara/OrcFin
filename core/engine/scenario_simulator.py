"""What-if scenario simulator — base vs adjusted financial projections."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.domain.month_format import format_month_year_label
from core.engine.reporting import _shift_month, get_balance_evolution_anchored


@dataclass
class ScenarioAdjustment:
    label: str
    monthly_income_delta: Decimal = Decimal("0")
    monthly_expense_delta: Decimal = Decimal("0")
    one_time_income: Decimal = Decimal("0")
    one_time_expense: Decimal = Decimal("0")


def simulate_scenario(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    months_ahead: int = 12,
    adjustments: Optional[List[ScenarioAdjustment]] = None,
    history_months: int = 12,
    end_year: Optional[int] = None,
    end_month: Optional[int] = None,
) -> Dict[str, Any]:
    """Project cumulative balance with and without hypothetical adjustments."""
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

    if not evolution:
        return {
            "base": [],
            "scenario": [],
            "summary": {},
            "adjustments": adjustments or [],
        }

    nets = [e["net_savings"] for e in evolution if e["net_savings"] != 0]
    avg_income = sum(e["income"] for e in evolution) / len(evolution)
    avg_expense = sum(e["expense"] for e in evolution) / len(evolution)
    avg_net = sum(nets) / len(nets) if nets else Decimal("0")

    adj = adjustments or []
    monthly_income_delta = sum(a.monthly_income_delta for a in adj)
    monthly_expense_delta = sum(a.monthly_expense_delta for a in adj)
    one_time_income = sum(a.one_time_income for a in adj)
    one_time_expense = sum(a.one_time_expense for a in adj)

    scenario_avg_net = avg_net + monthly_income_delta - monthly_expense_delta

    last = evolution[-1]
    base_cumulative = last["cumulative_balance"]
    scenario_cumulative = base_cumulative + one_time_income - one_time_expense

    base_points = []
    scenario_points = []
    base_cum = base_cumulative
    scen_cum = scenario_cumulative

    for offset in range(1, months_ahead + 1):
        y, m = _shift_month(anchor_year, anchor_month, offset)
        label = format_month_year_label(y, m)
        base_cum += avg_net
        scen_cum += scenario_avg_net
        base_points.append({
            "year": y,
            "month": m,
            "label": label,
            "projected_net": avg_net,
            "projected_cumulative": base_cum,
        })
        scenario_points.append({
            "year": y,
            "month": m,
            "label": label,
            "projected_net": scenario_avg_net,
            "projected_cumulative": scen_cum,
        })

    base_final = base_points[-1]["projected_cumulative"] if base_points else base_cumulative
    scenario_final = scenario_points[-1]["projected_cumulative"] if scenario_points else scenario_cumulative

    return {
        "base": base_points,
        "scenario": scenario_points,
        "adjustments": adj,
        "summary": {
            "current_cumulative": base_cumulative,
            "average_monthly_net": avg_net,
            "average_monthly_income": avg_income,
            "average_monthly_expense": avg_expense,
            "scenario_monthly_net": scenario_avg_net,
            "base_final_cumulative": base_final,
            "scenario_final_cumulative": scenario_final,
            "delta_cumulative": scenario_final - base_final,
            "months_ahead": months_ahead,
        },
    }


def parse_adjustment_from_form(
    label: str,
    income_delta: str = "0",
    expense_delta: str = "0",
    one_time_income: str = "0",
    one_time_expense: str = "0",
) -> ScenarioAdjustment:
    def _parse(val: str) -> Decimal:
        try:
            return Decimal(val.replace(",", ".").strip() or "0")
        except Exception:
            return Decimal("0")

    return ScenarioAdjustment(
        label=label or "Ajuste",
        monthly_income_delta=_parse(income_delta),
        monthly_expense_delta=_parse(expense_delta),
        one_time_income=_parse(one_time_income),
        one_time_expense=_parse(one_time_expense),
    )