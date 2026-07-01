"""Personal finance dashboard — KPIs, goals, and period overview."""
from __future__ import annotations

import flet as ft
from decimal import Decimal
from datetime import date

from core.domain.value_objects.money import format_brl
from core.engine.reporting import get_dashboard_data
from core.engine.due_dates import get_upcoming_due_dates
from core.engine.spendable import get_spendable_amount
from core.engine.local_insights import get_local_finance_insights
from core.db.repositories.goals import get_active_goals
from core.db.repositories.net_worth import get_net_worth_evolution, get_net_worth_totals
from ui.personal.period_filter import build_period_filter, period_label
from ui.theme import active as theme_colors, title_text, body_text
from ui.personal.charts import (
    section_card,
    category_breakdown_chart,
    balance_evolution_chart,
    budget_status_chart,
    income_expense_chart,
    net_worth_evolution_chart,
    projection_forecast_chart,
)

from ui.dashboard.cards import build_summary_card, format_change
from ui.dashboard.sections import (
    build_projection_section, build_insight_card, build_due_dates_section,
    build_decisions_section, build_insights_hub_section, build_net_worth_section,
    build_goals_section,
)

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
        current = self.data["current_month"]
        comparison = self.data["comparison"]
        evolution = self.data["balance_evolution"]
        projection = self.data["projection"]
        projection_detail = self.data.get("projection_detail", {})
        projection_chart = self.data.get("projection_chart", [])
        categories = self.data["category_breakdown"]
        category_title = "Despesas por categoria"
        if self.data.get("category_breakdown_is_projected"):
            category_title += " (projetado)"
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
            "month": "Saldo do Período",
            "ytd": "Economia YTD",
            "year": "Economia do Ano",
        }.get(period_mode, "Saldo do Período")

        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text(
                            "Dashboard" + (" • Visão Consolidada" if self.app.is_consolidated else " • Visão Individual"),
                        ),
                        body_text(period_text, size=13),
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
        cards_row = ft.Row(
            [
                build_summary_card(
                    summary_title,
                    format_brl(current["net_savings"]),
                    f"{current['savings_rate']}% de economia",
                    ft.Icons.ACCOUNT_BALANCE_WALLET,
                    "#14B8A6" if current["net_savings"] >= 0 else "#EF4444",
                ),
                build_summary_card(
                    "Quanto posso gastar",
                    format_brl(spend["spendable"]),
                    f"Após fixos, margem {spend['safety_pct']:.0f}% e gastos do mês",
                    ft.Icons.SAVINGS,
                    "#6366F1",
                ),
                build_summary_card(
                    "Receitas",
                    format_brl(current["total_income"]),
                    format_change(comparison["income_change_pct"]),
                    ft.Icons.TRENDING_UP,
                    "#22C55E",
                ),
                build_summary_card(
                    "Despesas",
                    format_brl(current["total_expense"]),
                    format_change(comparison["expense_change_pct"]),
                    ft.Icons.TRENDING_DOWN,
                    "#F97316",
                ),
            ],
            spacing=16,
            wrap=True,
        )

        chart_h = 260

        charts_row = ft.Row(
            [
                section_card(
                    category_title,
                    category_breakdown_chart(categories),
                    expand=True,
                    height=chart_h,
                ),
                section_card(
                    "Evolução do saldo (realizado)",
                    balance_evolution_chart(
                        evolution[-6:],
                        projection_points=None,
                        show_income_expense=False,
                    ),
                    expand=True,
                    height=chart_h,
                ),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        projection_section = build_projection_section(self, projection_detail)

        budget_month = self.data.get("budget_month", date.today().month)
        bottom_row = ft.Row(
            [
                section_card(
                    "Receita vs despesa (6 meses)",
                    income_expense_chart(monthly_series, compact=True, max_months=6),
                    expand=True,
                    height=chart_h,
                ),
                section_card(
                    f"Orçamentos de {budget_month:02d}/{self.data.get('period_year', date.today().year)}",
                    budget_status_chart(budgets),
                    expand=True,
                    height=chart_h,
                ),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        net_worth_section = build_net_worth_section(self)
        due_section = build_due_dates_section(self)

        return ft.Column(
            [
                header,
                ft.Container(height=24),
                cards_row,
                ft.Container(height=16),
                build_decisions_section(self),
                ft.Container(height=16),
                due_section,
                ft.Container(height=24),
                charts_row,
                ft.Container(height=16),
                projection_section,
                ft.Container(height=16),
                bottom_row,
                ft.Container(height=16),
                net_worth_section,
                ft.Container(height=24),
                build_insight_card(self, current, projection_detail),
                ft.Container(height=16),
                build_insights_hub_section(self),
                ft.Container(height=24),
                build_goals_section(self),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )