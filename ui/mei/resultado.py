"""MEI Resultado — P&L simplificado."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from core.i18n import t
from core.mei_pack import export_accountant_pack
from core.pdf_generator import generate_mei_monthly_result_pdf
from ui.mei.components import mei_text, mei_title, metric_card, section_card
from ui.mei.constants import MEI_ACCENT
from ui.theme import active as theme_colors, primary_button_style
from ui.mei.context import MeiContext, require_mei_ready


class MeiResultadoView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        report = self.ctx.report
        recon = self.ctx.reconciliation
        year = report.get("year", date.today().year)
        pid = self.ctx.profile_id
        period = {"month": date.today().month}

        def export_pdf(_):
            try:
                path = generate_mei_monthly_result_pdf(pid, year, period["month"], report)
                self.app.show_snack(t("mei.result.pdf_saved", path=path))
            except Exception as ex:
                self.app.show_snack(t("mei.result.pdf_error", error=ex), success=False)

        def export_pack(_):
            try:
                path = export_accountant_pack(pid, year, period["month"])
                self.app.show_snack(t("mei.result.pack_saved", path=path))
            except Exception as ex:
                self.app.show_snack(t("common.error", error=ex), success=False)

        def open_pack_guide(_):
            checklist = ft.Column(
                [
                    mei_text(t("mei.result.guide_1"), size=12),
                    mei_text(t("mei.result.guide_2"), size=12),
                    mei_text(t("mei.result.guide_3"), size=12),
                    mei_text(t("mei.result.guide_4"), size=12),
                    ft.Row(
                        [
                            ft.TextButton(t("common.close"), on_click=lambda _: self.app.close_modal()),
                            ft.ElevatedButton(
                                t("mei.result.generate_pack"),
                                on_click=lambda e: (self.app.close_modal(), export_pack(e)),
                                style=primary_button_style(bgcolor=MEI_ACCENT),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=8,
                tight=True,
            )
            self.app.show_modal(checklist, title=t("mei.result.pack_guide_title"))

        month_dd = ft.Dropdown(
            value=str(period["month"]),
            width=140,
            options=[ft.dropdown.Option(str(m), f"{m:02d}") for m in range(1, 13)],
            on_select=lambda e: period.update(month=int(e.control.value or period["month"])),
        )

        tc = theme_colors()
        header = ft.Row(
            [
                mei_title(t("mei.result.title", year=year)),
                month_dd,
                ft.Container(expand=True),
                ft.OutlinedButton(t("mei.result.pack_guide"), icon=ft.Icons.CHECKLIST, on_click=open_pack_guide),
                ft.OutlinedButton(t("mei.result.pack_btn"), icon=ft.Icons.FOLDER_ZIP, on_click=export_pack),
                ft.ElevatedButton(
                    t("mei.result.export_pdf"),
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                    style=primary_button_style(bgcolor=MEI_ACCENT),
                ),
            ],
            spacing=8,
        )

        kpis = ft.Row(
            [
                metric_card(t("mei.result.kpi_gross"), format_brl(report["gross_revenue"]), theme_colors().income, ft.Icons.TRENDING_UP),
                metric_card(t("mei.result.kpi_deductible"), format_brl(report["deductible_expenses"]), theme_colors().expense, ft.Icons.RECEIPT),
                metric_card(t("mei.result.kpi_non_deductible"), format_brl(report["non_deductible_expenses"]), theme_colors().text_muted, ft.Icons.BLOCK),
                metric_card(t("mei.result.kpi_result"), format_brl(report["simplified_result"]), MEI_ACCENT, ft.Icons.ACCOUNT_BALANCE),
            ],
            spacing=12,
        )

        formula = section_card(
            t("mei.result.how_to"),
            ft.Column(
                [
                    mei_text(t("mei.result.formula"), size=13),
                    mei_text(t("mei.result.disclaimer"), size=11, muted=True),
                    ft.Divider(color=tc.border),
                    mei_text(t("mei.result.tx_count", count=report.get("transaction_count", 0)), size=12, muted=True),
                    ft.Text(
                        t(
                            "mei.result.recon",
                            invoices=format_brl(recon.get("invoice_total", 0)),
                            recorded=format_brl(recon.get("recorded_income", 0)),
                        ),
                        color=theme_colors().success if recon.get("aligned") else theme_colors().warning,
                        size=12,
                    ),
                ],
                spacing=8,
            ),
        )

        return ft.Column(
            [header, ft.Container(height=16), kpis, ft.Container(height=16), formula],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
