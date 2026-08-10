"""Financial reports — YTD summaries, charts, trends, and AI analysis."""
from __future__ import annotations

import flet as ft
from datetime import date

from core.engine.reporting import (
    get_monthly_income_expense_series,
    get_year_to_date_summary,
)
from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from core.i18n import t
from core.models import TransactionType
from ui.personal.period_filter import build_period_filter, period_label
from ui.theme import active as theme_colors, body_text, on_surface_button_style, title_text
from ui.personal.charts import section_card, income_expense_chart

from ui.reports.sections import (
    build_category_trend_card,
    build_ytd_card,
    build_more_analyses,
)
from ui.reports.ai import build_ai_section


class ReportsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.profiles = get_all_profiles()
        self.categories = [
            c
            for c in get_categories_for_mode(self.app.is_mei_mode())
            if c.type == TransactionType.EXPENSE
        ]

    def build(self) -> ft.Control:
        c = theme_colors()
        context_label = self.app.get_view_context_label()
        profile_id = self.app.get_view_profile_id()
        consolidated = self.app.is_consolidated

        anchor_year = self.app.filter_year or date.today().year
        anchor_month = self.app.filter_month or date.today().month
        up_to = anchor_month if self.app.filter_month else None

        def export_pdf(_):
            from core.pdf_generator import generate_monthly_report

            try:
                path = generate_monthly_report(
                    self.app.filter_year or date.today().year,
                    self.app.filter_month or date.today().month,
                    consolidated=consolidated,
                    profile_id=profile_id,
                )
                self.app.show_snack(t("rep.pdf_done", path=path))
            except Exception as ex:
                self.app.show_snack(t("rep.pdf_error", error=ex), success=False)

        def export_csv(_):
            from core.data_export import export_report_summary_csv

            try:
                path = export_report_summary_csv(
                    year=anchor_year,
                    up_to_month=up_to or anchor_month,
                    profile_id=profile_id,
                    consolidated=consolidated,
                )
                self.app.show_snack(t("rep.csv_done", path=path))
            except Exception as ex:
                self.app.show_snack(t("rep.csv_error", error=ex), success=False)

        export_row = ft.Row(
            [
                ft.OutlinedButton(
                    t("rep.pdf_month"),
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                    style=on_surface_button_style(),
                    tooltip=t("rep.pdf_tooltip"),
                ),
                ft.OutlinedButton(
                    t("rep.csv_summary"),
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=export_csv,
                    style=on_surface_button_style(),
                    tooltip=t("rep.csv_tooltip"),
                ),
            ],
            spacing=8,
            wrap=True,
        )

        header = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                title_text(t("rep.title")),
                                body_text(
                                    f"{context_label} · {period_label(anchor_year, self.app.filter_month)}",
                                    size=13,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        build_period_filter(self.app),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
                export_row,
            ],
            spacing=10,
            tight=True,
        )

        ytd = get_year_to_date_summary(
            profile_id=profile_id,
            consolidated=consolidated,
            year=anchor_year,
            up_to_month=up_to,
        )
        prev_ytd = get_year_to_date_summary(
            profile_id=profile_id,
            consolidated=consolidated,
            year=anchor_year - 1,
            up_to_month=up_to or (date.today().month if anchor_year == date.today().year else 12),
        )
        # Only show YoY if previous year had activity
        if float(prev_ytd.get("total_income") or 0) == 0 and float(
            prev_ytd.get("total_expense") or 0
        ) == 0:
            prev_ytd = None

        ytd_title = t("rep.summary_year", year=anchor_year)
        if not self.app.filter_month and anchor_year == date.today().year:
            ytd_title += t("rep.summary_ytd_suffix")

        ytd_card = build_ytd_card(self, ytd, title=ytd_title, prev_ytd=prev_ytd)

        monthly_series = get_monthly_income_expense_series(
            months_back=12,
            end_year=anchor_year,
            end_month=anchor_month,
            profile_id=profile_id,
            consolidated=consolidated,
        )
        chart_h = 260
        charts_section = ft.Row(
            [
                section_card(
                    t("rep.income_vs_expense"),
                    income_expense_chart(monthly_series, compact=True, max_months=6),
                    expand=True,
                    height=chart_h,
                ),
                build_category_trend_card(
                    self,
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

        ai_section = build_ai_section(self)
        more = build_more_analyses(
            self,
            profile_id=profile_id,
            consolidated=consolidated,
            anchor_year=anchor_year,
            anchor_month=anchor_month,
        )

        # Hierarchy: status → AI → charts → deeper analyses (collapsed).
        # Do not put expand=True on children of this scroll Column (Flet/Flutter
        # then fills the viewport with one surface — often a blank gray block).
        return ft.Column(
            [
                header,
                ft.Container(height=16),
                ytd_card,
                ft.Container(height=16),
                ai_section,
                ft.Container(height=16),
                charts_section,
                ft.Container(height=16),
                more,
                ft.Container(height=16),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            tight=True,
            spacing=0,
        )
