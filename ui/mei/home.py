"""MEI Home — alertas, KPIs, gráficos."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from ui.mei.actions import confirm_das_for_context
from ui.mei.components import mei_banner, metric_card, section_card
from ui.mei.constants import MEI_ACCENT, MEI_BORDER, MEI_CARD
from ui.mei.context import MeiContext, require_mei_ready


class MeiHomeView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        ctx = self.ctx
        dash = ctx.dashboard
        alerts = self._alert_strip()
        kpis = ft.Row(
            [
                metric_card("Faturamento do mês", format_brl(dash["month_income"]), "#22C55E", ft.Icons.PAYMENTS),
                metric_card("Despesas do mês", format_brl(dash["month_expense"]), "#F97316", ft.Icons.SHOPPING_CART),
                metric_card("Resultado (ano)", format_brl(ctx.report.get("simplified_result", 0)), MEI_ACCENT, ft.Icons.INSIGHTS),
                metric_card(
                    "Ticket médio",
                    format_brl(dash["ticket_medio"]),
                    "#6366F1",
                    ft.Icons.PEOPLE,
                ),
            ],
            spacing=12,
        )

        charts = ft.Row(
            [
                self._limit_chart(),
                self._client_chart(dash.get("revenue_by_client", [])),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return ft.Column(
            [
                self._header(),
                ft.Container(height=8),
                mei_banner(),
                ft.Container(height=12),
                alerts,
                ft.Container(height=16),
                kpis,
                ft.Container(height=16),
                charts,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _header(self) -> ft.Control:
        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Início MEI", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(
                            f"{self.ctx.razao_social} • {self.ctx.cnpj}",
                            size=13,
                            color=ft.Colors.GREY_400,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.Text(date.today().strftime("%d/%m/%Y"), size=13, color=ft.Colors.GREY_400),
            ],
        )

    def _alert_strip(self) -> ft.Control:
        cards = []
        ctx = self.ctx

        if not ctx.das_paid:
            color = "#EF4444" if ctx.das_info.get("is_urgent") else MEI_ACCENT
            cards.append(self._alert_card(
                "DAS",
                f"Vence em {ctx.das_info.get('days_left', '?')} dia(s)",
                format_brl(ctx.das_amount),
                color,
                "Confirmar",
                self._confirm_das,
            ))

        if ctx.limit_status.get("at_risk"):
            cards.append(self._alert_card(
                "Limite MEI",
                f"{ctx.limit_status.get('percentage', 0):.0f}% do teto anual",
                format_brl(ctx.limit_status.get("ytd_revenue", 0)),
                "#EF4444",
                None,
                None,
            ))

        if not ctx.reconciliation.get("aligned") and ctx.reconciliation.get("invoice_count", 0) > 0:
            cards.append(self._alert_card(
                "Notas vs lançamentos",
                "Divergência detectada",
                format_brl(abs(ctx.reconciliation.get("difference", 0))),
                "#F59E0B",
                "Ver Notas",
                lambda _: self.app.switch_mei_tab(3),
            ))

        if not cards:
            cards.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color="#22C55E"),
                            ft.Text("Tudo em ordem este mês", color=ft.Colors.WHITE, size=13),
                        ],
                        spacing=8,
                    ),
                    bgcolor=MEI_CARD,
                    border_radius=10,
                    padding=16,
                    expand=True,
                )
            )

        return ft.Row(cards, spacing=12)

    def _alert_card(self, title, subtitle, value, color, btn_label, on_click) -> ft.Container:
        actions = []
        if btn_label and on_click:
            actions.append(
                ft.ElevatedButton(
                    btn_label,
                    on_click=on_click,
                    style=ft.ButtonStyle(bgcolor=color, color=ft.Colors.WHITE),
                )
            )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=color),
                    ft.Text(subtitle, size=11, color=ft.Colors.GREY_400),
                    ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    *actions,
                ],
                spacing=6,
            ),
            bgcolor=MEI_CARD,
            border=ft.Border.all(1, color),
            border_radius=12,
            padding=16,
            expand=True,
        )

    def _confirm_das(self, _):
        confirm_das_for_context(self.app, self.ctx)

    def _limit_chart(self) -> ft.Container:
        evolution = self.ctx.dashboard.get("ytd_evolution", [])
        limit = self.ctx.annual_limit
        rows = []
        for pt in evolution:
            pct = float(pt["cumulative"] / limit * 100) if limit > 0 else 0
            bar_color = "#EF4444" if pct >= 80 else MEI_ACCENT
            rows.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(pt["label"], size=11, width=60, color=ft.Colors.GREY_400),
                                ft.Container(
                                    content=ft.Container(height=8, bgcolor=bar_color, border_radius=4),
                                    width=max(4, min(200, int(pct * 2))),
                                    bgcolor=MEI_BORDER,
                                    border_radius=4,
                                    height=8,
                                ),
                                ft.Text(format_brl(pt["cumulative"]), size=10, color=ft.Colors.WHITE),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=2,
                )
            )

        return section_card(
            f"Faturamento acumulado vs limite ({format_brl(limit)})",
            ft.Column(rows if rows else [ft.Text("Sem receitas no ano", color=ft.Colors.GREY_500)], spacing=6),
        )

    def _client_chart(self, by_client: list) -> ft.Container:
        if not by_client:
            body = ft.Text("Vincule receitas a clientes na aba Vendas", color=ft.Colors.GREY_500, size=12)
        else:
            body = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(row["name"][:28], size=11, expand=True, color=ft.Colors.GREY_300),
                            ft.Text(format_brl(row["total"]), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ],
                    )
                    for row in by_client[:8]
                ],
                spacing=6,
            )
        return section_card("Receita por cliente (ano)", body)