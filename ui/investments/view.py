"""Investments portfolio — holdings and quotes."""

from __future__ import annotations

import flet as ft

from core.domain.value_objects.money import format_brl
from core.i18n import t
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
from ui.theme import (
    active as theme_colors,
    body_text,
    empty_state,
    primary_button_style,
    signed_label,
    status_color,
    title_text,
)


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
                self.error = t("inv.load_error", error=ex)

    def build(self) -> ft.Control:
        context_label = self.app.get_view_context_label()
        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text(t("inv.title")),
                        body_text(
                            f"{context_label} • {period_label(self.app.filter_year, self.app.filter_month)}",
                            size=13,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    t("inv.refresh"),
                    icon=ft.Icons.REFRESH,
                    on_click=self._refresh_quotes,
                    disabled=not quotes_enabled(self.app.settings),
                    tooltip=t("inv.refresh_tooltip"),
                ),
                ft.ElevatedButton(
                    t("inv.new"),
                    icon=ft.Icons.ADD_CHART,
                    on_click=lambda _: open_holding_form(self.app, on_saved=self._reload),
                    style=primary_button_style(bgcolor=theme_colors().accent_portfolio),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        c = theme_colors()
        if self.app.is_consolidated:
            body = empty_state(
                icon=ft.Icons.PERSON_OUTLINE,
                title=t("inv.consolidated_title"),
                message=t("inv.consolidated_msg"),
                accent=c.accent_portfolio,
            )
            return ft.Column([header, ft.Container(height=16), body], expand=True)

        if self.error:
            body = empty_state(
                icon=ft.Icons.ERROR_OUTLINE,
                title=t("inv.load_error_title"),
                message=self.error,
                accent=c.danger,
            )
            return ft.Column([header, ft.Container(height=16), body], expand=True)

        if not self.summary or not self.summary["holdings"]:
            offline_hint = ""
            if not quotes_enabled(self.app.settings):
                offline_hint = t("inv.empty_offline_hint")
            body = empty_state(
                icon=ft.Icons.TRENDING_UP,
                title=t("inv.empty_title"),
                message=t("inv.empty_msg") + offline_hint,
                action_label=t("inv.new"),
                on_action=lambda _: open_holding_form(self.app, on_saved=self._reload),
                accent=c.accent_portfolio,
            )
            return ft.Column([header, ft.Container(height=16), body], expand=True, scroll=ft.ScrollMode.AUTO)

        totals = self.summary["totals"]
        cost = totals["cost_basis"]
        pnl = totals["pnl"]
        pnl_pct = float((pnl / cost) * 100) if cost > 0 else 0.0
        summary_row = ft.Row(
            [
                self._metric_card(t("inv.market_value"), format_brl(totals["market_value"]), c.accent_portfolio),
                self._metric_card(t("inv.total_cost"), format_brl(cost), c.text_secondary),
                self._metric_card(
                    t("inv.result"),
                    f"{format_brl(pnl)} · {signed_label(pnl_pct)}",
                    status_color(positive=pnl >= 0),
                ),
            ],
            spacing=16,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        holdings_table = section_card(
            t("inv.holdings_title"),
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
            self.app.show_snack(t("inv.quotes_error", error=ex), success=False)
            return
        self.app.show_snack(
            t("inv.quotes_done", updated=result["updated"], failed=result["failed"])
        )
        self._reload()
