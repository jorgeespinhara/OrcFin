"""MEI Resultado — P&L simplificado."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from core.mei_pack import export_accountant_pack
from core.pdf_generator import generate_mei_monthly_result_pdf
from ui.mei.components import metric_card, section_card
from ui.mei.constants import MEI_ACCENT, MEI_BORDER
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
        month = date.today().month

        def export_pdf(_):
            try:
                path = generate_mei_monthly_result_pdf(pid, year, month, report)
                self.app.show_snack(f"PDF salvo em: {path}")
            except Exception as ex:
                self.app.show_snack(f"Erro ao gerar PDF: {ex}", success=False)

        def export_pack(_):
            try:
                path = export_accountant_pack(pid, year, month)
                self.app.show_snack(f"Pacote contador: {path}")
            except Exception as ex:
                self.app.show_snack(f"Erro: {ex}", success=False)

        header = ft.Row(
            [
                ft.Text(f"Resultado {year}", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(expand=True),
                ft.OutlinedButton("Pacote contador", icon=ft.Icons.FOLDER_ZIP, on_click=export_pack),
                ft.ElevatedButton(
                    "Exportar PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                    style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                ),
            ],
            spacing=8,
        )

        kpis = ft.Row(
            [
                metric_card("Receita bruta", format_brl(report["gross_revenue"]), "#22C55E", ft.Icons.TRENDING_UP),
                metric_card("Desp. dedutíveis", format_brl(report["deductible_expenses"]), "#F97316", ft.Icons.RECEIPT),
                metric_card("Desp. não dedut.", format_brl(report["non_deductible_expenses"]), "#94A3B8", ft.Icons.BLOCK),
                metric_card("Resultado", format_brl(report["simplified_result"]), MEI_ACCENT, ft.Icons.ACCOUNT_BALANCE),
            ],
            spacing=12,
        )

        formula = section_card(
            "Como interpretar",
            ft.Column(
                [
                    ft.Text("Resultado simplificado = Receita bruta − Despesas dedutíveis", color=ft.Colors.GREY_300, size=13),
                    ft.Text("Não substitui contabilidade formal. Serve para visão rápida do negócio.", color=ft.Colors.GREY_500, size=11),
                    ft.Divider(color=MEI_BORDER),
                    ft.Text(f"Lançamentos no ano: {report.get('transaction_count', 0)}", color=ft.Colors.GREY_400, size=12),
                    ft.Text(
                        f"Notas fiscais: {format_brl(recon.get('invoice_total', 0))} | "
                        f"Lançamentos: {format_brl(recon.get('recorded_income', 0))}",
                        color="#22C55E" if recon.get("aligned") else "#F59E0B",
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