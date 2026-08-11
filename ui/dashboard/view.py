"""Personal finance dashboard — KPIs, goals, and period overview."""
from __future__ import annotations

import flet as ft
from datetime import date

from core.domain.value_objects.money import format_brl
from core.engine.reporting import get_dashboard_data
from core.engine.spendable import get_spendable_amount
from core.i18n import t
from ui.personal.period_filter import build_period_filter, period_label
from ui.theme import active as theme_colors, body_text, collapsible_section, format_change, title_text
from ui.personal.charts import (
    section_card,
    category_breakdown_chart,
    balance_evolution_chart,
    income_expense_chart,
)

from ui.dashboard.cards import build_summary_card, build_spendable_card
from ui.dashboard.sections import (
    build_projection_section,
    build_insight_card,
    build_due_dates_section,
    build_decisions_section,
    build_net_worth_section,
    build_net_worth_strip_section,
    build_portfolio_section,
    build_goals_section,
    build_budget_section,
    run_dashboard_action,
)


def _is_blank(control: ft.Control) -> bool:
    """True for empty placeholder containers (no content to show)."""
    return isinstance(control, ft.Container) and control.content is None


class DashboardView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.data = get_dashboard_data(
            profile_id=app.get_view_profile_id(),
            consolidated=app.is_consolidated,
            year=app.filter_year,
            month=app.filter_month,
            projection_months_ahead=app.projection_months_ahead,
        )

    def build(self) -> ft.Control:
        c = theme_colors()
        current = self.data["current_month"]
        comparison = self.data["comparison"]
        evolution = self.data["balance_evolution"]
        projection_detail = self.data.get("projection_detail", {})
        categories = self.data["category_breakdown"]
        category_title = t("dash.expenses_by_category")
        if self.data.get("category_breakdown_is_projected"):
            category_title += t("dash.projected_suffix")
        monthly_series = self.data.get("monthly_series", [])
        budgets = self.data.get("budgets", [])
        period_mode = self.data.get("period_mode", "month")

        period_text = period_label(
            self.data.get("period_year", date.today().year),
            self.data.get("period_month"),
        )
        if period_mode == "ytd":
            period_text = f"YTD {period_text}"

        summary_title = {
            "month": t("dash.balance_period"),
            "ytd": t("dash.savings_ytd"),
            "year": t("dash.savings_year"),
        }.get(period_mode, t("dash.balance_period"))

        context = self.app.get_view_context_label()
        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text(t("dash.title")),
                        body_text(f"{context} · {period_text}", size=13),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                build_period_filter(self.app),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        spend = get_spendable_amount(
            profile_id=self.app.get_view_profile_id(),
            consolidated=self.app.is_consolidated,
            year=self.data.get("period_year"),
            month=self.data.get("period_month") or date.today().month,
        )

        series_tail = monthly_series[-6:]
        income_spark = [float(p.get("income") or 0) for p in series_tail]
        expense_spark = [float(p.get("expense") or 0) for p in series_tail]
        net_spark = [float(p.get("net_savings") or 0) for p in series_tail]

        # Band 1 — status KPIs (sparklines on income / expense / balance)
        cards_row = ft.Row(
            [
                build_summary_card(
                    summary_title,
                    format_brl(current["net_savings"]),
                    t("dash.savings_rate", rate=current["savings_rate"]),
                    ft.Icons.ACCOUNT_BALANCE_WALLET,
                    c.success if current["net_savings"] >= 0 else c.danger,
                    on_click=lambda _: run_dashboard_action(self.app, "reports"),
                    tooltip=t("dash.tip_reports"),
                    sparkline_values=net_spark,
                ),
                build_spendable_card(
                    format_brl(spend["spendable"]),
                    spend,
                    on_click=lambda _: run_dashboard_action(self.app, "budgets"),
                    tooltip=t("dash.tip_budgets"),
                ),
                build_summary_card(
                    t("dash.income"),
                    format_brl(current["total_income"]),
                    format_change(comparison["income_change_pct"]),
                    ft.Icons.TRENDING_UP,
                    c.income,
                    on_click=lambda _: run_dashboard_action(self.app, "transactions"),
                    tooltip=t("dash.tip_transactions"),
                    sparkline_values=income_spark,
                ),
                build_summary_card(
                    t("dash.expense"),
                    format_brl(current["total_expense"]),
                    format_change(comparison["expense_change_pct"]),
                    ft.Icons.TRENDING_DOWN,
                    c.expense,
                    on_click=lambda _: run_dashboard_action(self.app, "transactions"),
                    tooltip=t("dash.tip_transactions"),
                    sparkline_values=expense_spark,
                ),
            ],
            spacing=16,
            wrap=True,
        )

        chart_h = 320
        hero_h = 340
        budget_month = self.data.get("budget_month", date.today().month)
        period_year = self.data.get("period_year", date.today().year)
        exp_pct = comparison.get("expense_change_pct")
        inc_pct = comparison.get("income_change_pct")

        # Band 2 — three open charts: categories, cashflow (12m), budgets
        hero_chart = section_card(
            category_title,
            category_breakdown_chart(categories, expense_change_pct=exp_pct),
            height=hero_h,
        )

        cashflow_chart = section_card(
            t("dash.income_vs_expense_12"),
            income_expense_chart(
                monthly_series,
                compact=True,
                max_months=12,
                expense_change_pct=exp_pct,
                income_change_pct=inc_pct,
            ),
            height=chart_h + 40,
        )

        context_charts = ft.Row(
            [
                section_card(
                    t("dash.balance_evolution"),
                    balance_evolution_chart(
                        evolution[-12:],
                        projection_points=None,
                        show_income_expense=False,
                    ),
                    expand=True,
                    height=chart_h,
                ),
                build_budget_section(self, budgets, budget_month, period_year),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Band 4 — wealth + projection collapsed (charts above stay open)
        detail_blocks: list[ft.Control] = []
        wealth_parts: list[ft.Control] = []
        nw = build_net_worth_section(self)
        if not _is_blank(nw):
            wealth_parts.append(nw)
        portfolio = build_portfolio_section(self)
        if not _is_blank(portfolio):
            wealth_parts.append(portfolio)
        if wealth_parts:
            detail_blocks.append(
                collapsible_section(
                    t("dash.wealth_section"),
                    ft.Column(wealth_parts, spacing=12, tight=True),
                    expanded=False,
                    subtitle=t("dash.wealth_collapse_sub"),
                )
            )
        detail_blocks.append(
            collapsible_section(
                t("dash.more_analysis"),
                build_projection_section(self, projection_detail),
                expanded=False,
                subtitle=t("dash.more_analysis_sub"),
            )
        )

        # Hierarchy: KPIs → NW strip → insight → charts → bills → decisions → collapsed wealth
        nw_strip = build_net_worth_strip_section(self)
        body: list[ft.Control] = [
            header,
            ft.Container(height=16),
            cards_row,
        ]
        if not _is_blank(nw_strip):
            body.extend([ft.Container(height=12), nw_strip])
        body.extend(
            [
                ft.Container(height=12),
                build_insight_card(self, current, projection_detail),
                ft.Container(height=16),
                hero_chart,
                ft.Container(height=16),
                cashflow_chart,
                ft.Container(height=16),
                context_charts,
                ft.Container(height=12),
                build_due_dates_section(self),
                ft.Container(height=12),
                build_decisions_section(self),
            ]
        )
        for block in detail_blocks:
            body.extend([ft.Container(height=12), block])
        body.extend(
            [
                ft.Container(height=16),
                build_goals_section(self),
            ]
        )

        return ft.Column(
            body,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            tight=False,
            spacing=0,
        )
