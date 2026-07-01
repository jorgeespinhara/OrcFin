"""MEI Resultado — P&L simplificado."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from core.mei_pack import export_accountant_pack
from core.pdf_generator import generate_mei_monthly_result_pdf
from ui.mei.components import mei_text, mei_title, metric_card, section_card
from ui.mei.constants import MEI_ACCENT
from ui.theme import active as theme_colors
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
                self.app.show_snack(f"PDF salvo em: {path}")
            except Exception as ex:
                self.app.show_snack(f"Erro ao gerar PDF: {ex}", success=False)

        def export_pack(_):
            try:
                path = export_accountant_pack(pid, year, period["month"])
                self.app.show_snack(f"Pacote contador: {path}")
            except Exception as ex:
                self.app.show_snack(f"Erro: {ex}", success=False)

        def open_pack_guide(_):
            checklist = ft.Column(
                [
                    mei_text("1. Conferir lançamentos do mês", size=12),
                    mei_text("2. Conferir notas fiscais emitidas", size=12),
                    mei_text("3. Verificar DAS pago em Obrigações", size=12),
                    mei_text("4. Gerar pacote ZIP e enviar ao contador", size=12),
                    ft.Row(
                        [
                            ft.TextButton("Fechar", on_click=lambda _: self.app.close_modal()),
                            ft.ElevatedButton(
                                "Gerar pacote",
                                on_click=lambda e: (self.app.close_modal(), export_pack(e)),
                                style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=8,
                tight=True,
            )
            self.app.show_modal(checklist, title="Pacote contador")

        month_dd = ft.Dropdown(
            value=str(period["month"]),
            width=140,
            options=[ft.dropdown.Option(str(m), f"{m:02d}") for m in range(1, 13)],
            on_select=lambda e: period.update(month=int(e.control.value or period["month"])),
        )

        tc = theme_colors()
        header = ft.Row(
            [
                mei_title(f"Resultado {year}"),
                month_dd,
                ft.Container(expand=True),
                ft.OutlinedButton("Guia do pacote", icon=ft.Icons.CHECKLIST, on_click=open_pack_guide),
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
                    mei_text("Resultado simplificado = Receita bruta − Despesas dedutíveis", size=13),
                    mei_text("Não substitui contabilidade formal. Serve para visão rápida do negócio.", size=11, muted=True),
                    ft.Divider(color=tc.border),
                    mei_text(f"Lançamentos no ano: {report.get('transaction_count', 0)}", size=12, muted=True),
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