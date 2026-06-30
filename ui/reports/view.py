"""Financial reports — YTD summaries, charts, trends, and AI analysis."""
from __future__ import annotations

import flet as ft
from datetime import date

from core.domain.value_objects.money import format_brl
from core.engine.reporting import (
    get_monthly_income_expense_series,
    get_top_expense_categories_with_trend,
    get_year_to_date_summary,
)
from core.ai_gateway import PROVIDERS, get_financial_insights, provider_is_configured
from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from core.models import TransactionType
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights
from core.engine.scenario_simulator import simulate_scenario, parse_adjustment_from_form
from core.engine.recurrence_detection import detect_recurring_transactions
from ui.personal.period_filter import build_period_filter, period_label
from ui.theme import active as theme_colors, title_text, body_text
from ui.personal.charts import (
    section_card,
    income_expense_chart,
    category_trend_chart,
    seasonal_comparison_chart,
    scenario_comparison_chart,
)

from ui.reports.sections import mini_metric, build_category_trend_card, build_seasonal_section, build_scenario_section, build_recurrence_section
from ui.reports.ai import build_ai_section

class ReportsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.profiles = get_all_profiles()
        self.categories = [
            c for c in get_categories_for_mode(self.app.is_mei_mode())
            if c.type == TransactionType.EXPENSE
        ]

    def build(self) -> ft.Control:
        context_label = self.app.get_view_context_label()
        profile_id = self.app.get_view_profile_id()
        consolidated = self.app.is_consolidated

        anchor_year = self.app.filter_year or date.today().year
        anchor_month = self.app.filter_month or date.today().month

        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text("Relatórios & Inteligência Artificial"),
                        body_text(
                            f"{context_label} • {period_label(anchor_year, self.app.filter_month)}",
                            size=13,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                build_period_filter(self.app),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        ytd = get_year_to_date_summary(
            profile_id=profile_id,
            consolidated=consolidated,
            year=anchor_year,
            up_to_month=anchor_month if self.app.filter_month else None,
        )
        ytd_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"Resumo {anchor_year}" + (" (YTD)" if not self.app.filter_month and anchor_year == date.today().year else ""),
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme_colors().text_primary,
                    ),
                    ft.Row(
                        [
                            mini_metric("Receita", format_brl(ytd["total_income"])),
                            mini_metric("Despesa", format_brl(ytd["total_expense"])),
                            mini_metric("Economia", format_brl(ytd["net_savings"])),
                            mini_metric("Taxa de Poupança", f"{ytd['savings_rate']}%"),
                        ],
                        spacing=24,
                        wrap=True,
                    ),
                ],
                spacing=16,
            ),
            padding=24,
            bgcolor=theme_colors().surface,
            border_radius=16,
        )

        monthly_series = get_monthly_income_expense_series(
            months_back=12,
            end_year=anchor_year,
            end_month=anchor_month,
            profile_id=profile_id,
            consolidated=consolidated,
        )
        chart_h = 240
        charts_section = ft.Row(
            [
                section_card(
                    "Receita vs despesa (6 meses)",
                    income_expense_chart(monthly_series, compact=True, max_months=6),
                    expand=True,
                    height=chart_h,
                ),
                build_category_trend_card(self, 
                    profile_id,
                    consolidated,
                    anchor_year,
                    anchor_month,
                    height=chart_h,
                ),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        seasonal_section = build_seasonal_section(self, profile_id, consolidated, anchor_year)
        scenario_section = build_scenario_section(self, profile_id, consolidated, anchor_year, anchor_month)
        recurrence_section = build_recurrence_section(self, profile_id, consolidated)
        ai_section = build_ai_section(self)

        return ft.Column(
            [
                header,
                ft.Container(height=24),
                ytd_card,
                ft.Container(height=24),
                charts_section,
                ft.Container(height=24),
                seasonal_section,
                ft.Container(height=24),
                scenario_section,
                ft.Container(height=24),
                recurrence_section,
                ft.Container(height=32),
                ai_section,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )