"""Investments portfolio — holdings and quotes."""

from __future__ import annotations

import flet as ft

from core.domain.value_objects.money import format_brl
from core.network_policy import BLOCKED_MESSAGE
from core.services.portfolio_service import (
    get_portfolio_summary,
    invalidate_portfolio_summary_cache,
    quotes_enabled,
    refresh_quotes,
)
from ui.investments.form import open_holding_form
from ui.investments.table import build_holdings_table
from ui.personal.charts import section_card
from ui.personal.period_filter import period_label
from ui.theme import active as theme_colors, title_text, body_text

_PORTFOLIO_ACCENT = "#6366F1"


class InvestmentsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        profile_id = app.get_view_profile_id()
        self.error: str | None = None
        self.summary = None
        if profile_id and not app.is_consolidated:
            try:
                self.summary = get_portfolio_summary(profile_id, settings=app.settings)
            except Exception as ex:
                self.error = f"Não foi possível carregar a carteira: {ex}"

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
                    "Atualizar agora",
                    icon=ft.Icons.REFRESH,
                    on_click=self._refresh_quotes,
                    disabled=not quotes_enabled(self.app.settings),
                    tooltip="Cotações também atualizam automaticamente a cada 15 minutos",
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
            body = self._message_card([
                ft.Text(
                    "Selecione um perfil individual para gerenciar investimentos.",
                    color=theme_colors().text_muted,
                    size=14,
                ),
            ])
            return ft.Column([header, ft.Container(height=16), body], expand=True)

        if self.error:
            body = self._message_card([
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=40, color=theme_colors().error_text),
                ft.Text(self.error, size=13, color=theme_colors().text_muted),
            ])
            return ft.Column([header, ft.Container(height=16), body], expand=True)

        if not self.summary or not self.summary["holdings"]:
            offline_hint = ""
            if not quotes_enabled(self.app.settings):
                offline_hint = " Cotações externas desativadas (offline estrito ou configuração)."
            body = self._message_card([
                ft.Icon(ft.Icons.TRENDING_UP, size=48, color=_PORTFOLIO_ACCENT),
                ft.Text("Nenhuma posição cadastrada", size=16, color=theme_colors().text_primary),
                ft.Text(
                    "Cadastre ações, FIIs, fundos (CNPJ via CVM), ETFs ou cripto." + offline_hint,
                    size=13,
                    color=theme_colors().text_muted,
                    text_align=ft.TextAlign.CENTER,
                ),
            ])
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
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        holdings_table = section_card(
            "Posições da carteira",
            build_holdings_table(self.summary["holdings"], self.app, on_reload=self._reload),
            scroll_content=False,
        )

        return ft.Column(
            [
                header,
                ft.Container(height=16),
                summary_row,
                ft.Container(height=16),
                holdings_table,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _message_card(self, controls: list[ft.Control]) -> ft.Container:
        return ft.Container(
            padding=32,
            bgcolor=theme_colors().surface,
            border_radius=16,
            border=ft.Border.all(1, theme_colors().border),
            content=ft.Column(
                controls,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
        )

    def _metric_card(self, title: str, value: str, color: str) -> ft.Container:
        return ft.Container(
            width=260,
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
                tight=True,
            ),
        )

    def _reload(self):
        profile_id = self.app.get_view_profile_id()
        if profile_id:
            invalidate_portfolio_summary_cache(profile_id)
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