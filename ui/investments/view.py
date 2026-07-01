"""Investments portfolio — holdings, quotes, and charts."""

from __future__ import annotations

import flet as ft

from core.db.repositories.investment_holdings import delete_holding
from core.domain.value_objects.money import format_brl
from core.network_policy import BLOCKED_MESSAGE
from core.services.portfolio_service import get_portfolio_summary, quotes_enabled, refresh_quotes
from ui.investments.form import open_holding_form
from ui.personal.charts import PERSONAL_ACCENT, horizontal_bar_chart, section_card
from ui.personal.period_filter import period_label
from ui.theme import active as theme_colors, title_text, body_text

_PORTFOLIO_ACCENT = "#6366F1"


class _PortfolioEvolutionChart:
    """Simple line-style chart from portfolio snapshots."""

    @staticmethod
    def build(points: list[dict]) -> ft.Control:
        if not points:
            return ft.Text("Sem histórico ainda.", size=12, color=theme_colors().text_muted)
        values = [float(p.get("total_value", 0)) for p in points]
        max_v = max(values) or 1.0
        bars = []
        for pt in points[-12:]:
            v = float(pt.get("total_value", 0))
            h = max(4, int(80 * v / max_v))
            bars.append(
                ft.Column(
                    [
                        ft.Container(height=h, width=18, bgcolor=_PORTFOLIO_ACCENT, border_radius=4),
                        ft.Text(pt.get("label", ""), size=9, color=theme_colors().text_muted),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                )
            )
        return ft.Row(bars, spacing=8, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END)


class InvestmentsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        profile_id = app.get_view_profile_id()
        self.summary = (
            get_portfolio_summary(profile_id, settings=app.settings)
            if profile_id and not app.is_consolidated
            else None
        )

    def build(self) -> ft.Control:
        context_label = self.app.get_view_context_label()
        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text("Investimentos"),
                        body_text(
                            f"{context_label} • {period_label(self.app.filter_year, self.app.filter_month)}",
                            size=13,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    "Atualizar cotações",
                    icon=ft.Icons.REFRESH,
                    on_click=self._refresh_quotes,
                    disabled=not quotes_enabled(self.app.settings),
                ),
                ft.ElevatedButton(
                    "Nova posição",
                    icon=ft.Icons.ADD_CHART,
                    on_click=lambda _: open_holding_form(self.app, on_saved=self._reload),
                    style=ft.ButtonStyle(bgcolor=_PORTFOLIO_ACCENT, color=theme_colors().text_primary),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        if self.app.is_consolidated:
            body = ft.Container(
                padding=24,
                content=ft.Text(
                    "Selecione um perfil individual para gerenciar investimentos.",
                    color=theme_colors().text_muted,
                    size=14,
                ),
            )
            return ft.Column([header, ft.Container(height=16), body], expand=True)

        if not self.summary or not self.summary["holdings"]:
            offline_hint = ""
            if not quotes_enabled(self.app.settings):
                offline_hint = " Cotações externas desativadas (offline estrito ou configuração)."
            body = ft.Container(
                padding=32,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.TRENDING_UP, size=48, color=_PORTFOLIO_ACCENT),
                        ft.Text("Nenhuma posição cadastrada", size=16, color=theme_colors().text_primary),
                        ft.Text(
                            "Cadastre ações, FIIs, fundos (CNPJ via CVM), ETFs ou cripto."
                            + offline_hint,
                            size=13,
                            color=theme_colors().text_muted,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
            )
            return ft.Column([header, ft.Container(height=16), body], expand=True, scroll=ft.ScrollMode.AUTO)

        totals = self.summary["totals"]
        summary_row = ft.Row(
            [
                self._metric_card("Valor de mercado", format_brl(totals["market_value"]), _PORTFOLIO_ACCENT),
                self._metric_card("Custo total", format_brl(totals["cost_basis"]), theme_colors().text_secondary),
                self._metric_card(
                    "Resultado",
                    format_brl(totals["pnl"]),
                    "#22C55E" if totals["pnl"] >= 0 else "#EF4444",
                ),
            ],
            spacing=16,
            wrap=True,
        )

        allocation = self.summary.get("allocation") or []
        charts = ft.Row(
            [
                section_card(
                    "Alocação por classe",
                    horizontal_bar_chart(allocation, label_key="label", value_key="value"),
                    expand=True,
                    height=220,
                ),
                section_card(
                    "Evolução da carteira",
                    _PortfolioEvolutionChart.build(self.summary.get("evolution") or []),
                    expand=True,
                    height=220,
                ),
            ],
            spacing=16,
        )

        holdings_list = ft.Column(
            [self._holding_tile(item) for item in self.summary["holdings"]],
            spacing=10,
        )

        return ft.Column(
            [header, ft.Container(height=16), summary_row, ft.Container(height=16), charts,
             ft.Container(height=16), holdings_list],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _metric_card(self, title: str, value: str, color: str) -> ft.Container:
        return ft.Container(
            padding=16,
            bgcolor=theme_colors().surface,
            border_radius=12,
            border=ft.Border.all(1, theme_colors().border),
            content=ft.Column(
                [
                    ft.Text(title, size=12, color=theme_colors().text_muted),
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
                ],
                spacing=4,
            ),
            expand=True,
        )

    def _holding_tile(self, item: dict) -> ft.Container:
        holding = item["holding"]
        price_txt = format_brl(item["price"]) if item["has_quote"] else "n/d"
        pnl_color = "#22C55E" if item["pnl"] >= 0 else "#EF4444"

        def edit(_):
            open_holding_form(self.app, holding=holding, on_saved=self._reload)

        def remove(_):
            delete_holding(holding.id)
            self.app.show_snack("Posição removida.")
            self._reload()

        identifier = holding.symbol or holding.cnpj or "-"
        return ft.Container(
            padding=16,
            bgcolor=theme_colors().surface,
            border_radius=12,
            border=ft.Border.all(1, theme_colors().border),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(holding.name, size=15, weight=ft.FontWeight.W_600),
                            ft.Text(
                                f"{item['asset_class_label']} • {identifier}"
                                + (f" • {holding.broker}" if holding.broker else ""),
                                size=11,
                                color=theme_colors().text_muted,
                            ),
                            ft.Text(
                                f"Qtd {holding.quantity} • PM {format_brl(holding.avg_cost)} • Cota {price_txt}",
                                size=11,
                                color=theme_colors().text_secondary,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Text(format_brl(item["market_value"]), size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"{item['pnl_pct']:+.1f}% ({format_brl(item['pnl'])})",
                                size=11,
                                color=pnl_color,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=2,
                    ),
                    ft.IconButton(ft.Icons.EDIT, icon_size=18, tooltip="Editar", on_click=edit),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, tooltip="Excluir", on_click=remove),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _reload(self):
        self.app.refresh_current_view()

    def _refresh_quotes(self, _=None):
        profile_id = self.app.get_view_profile_id()
        if not profile_id:
            return
        if not quotes_enabled(self.app.settings):
            self.app.show_snack(BLOCKED_MESSAGE, success=False)
            return
        try:
            result = refresh_quotes(profile_id, self.app.settings)
        except PermissionError as ex:
            self.app.show_snack(str(ex), success=False)
            return
        except Exception as ex:
            self.app.show_snack(f"Erro ao atualizar cotações: {ex}", success=False)
            return
        self.app.show_snack(
            f"Cotações: {result['updated']} atualizada(s), {result['failed']} sem cotação."
        )
        self._reload()