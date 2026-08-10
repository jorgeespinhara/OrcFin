"""MEI Obrigações — DAS, limite, checklist mensal."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from core.i18n import t
from core.mei import get_obligations_checklist
from core.mei_calendar import export_das_ics
from ui.mei.actions import confirm_das_for_context
from core.mei_tax import simulate_me_migration, ME_MIGRATION_THRESHOLD_PCT
from ui.mei.components import mei_card, mei_heading, mei_text, mei_title, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.theme import active as theme_colors, primary_button_style


class MeiObrigacoesView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        ctx = self.ctx
        checklist = get_obligations_checklist(ctx.profile_id)
        limit = ctx.limit_status
        tc = theme_colors()

        header = mei_title(t("mei.obligations.title"))

        das_card = mei_card(
            ft.Column(
                [
                    mei_heading(t("mei.obligations.das_heading")),
                    ft.Text(format_brl(ctx.das_amount), size=32, weight=ft.FontWeight.BOLD, color=MEI_ACCENT),
                    mei_text(
                        t("mei.obligations.das_paid")
                        if ctx.das_paid
                        else t(
                            "mei.obligations.das_due",
                            day=f"{ctx.das_info.get('due_date', date.today()).day:02d}",
                            days=ctx.das_info.get("days_left"),
                        ),
                        size=13,
                        muted=True,
                    ),
                    mei_text(t("mei.obligations.das_hint"), size=11, muted=True, italic=True),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                t("mei.obligations.confirm_das"),
                                icon=ft.Icons.CHECK,
                                disabled=ctx.das_paid,
                                on_click=self._confirm_das,
                                style=primary_button_style(bgcolor=MEI_ACCENT),
                            ),
                            ft.OutlinedButton(
                                t("mei.obligations.export_ics"),
                                icon=ft.Icons.CALENDAR_MONTH,
                                on_click=self._export_das_calendar,
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
            expand=True,
        )

        limit_card = mei_card(
            ft.Column(
                [
                    mei_heading(t("mei.obligations.limit_heading")),
                    ft.Text(
                        f"{format_brl(limit.get('ytd_revenue', 0))} / {format_brl(limit.get('annual_limit', 0))}",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=tc.text_primary,
                    ),
                    ft.ProgressBar(
                        value=min(limit.get("percentage", 0) / 100, 1.0),
                        color=theme_colors().danger if limit.get("at_risk") else MEI_ACCENT,
                        bgcolor=tc.surface_alt,
                    ),
                    mei_text(t("mei.obligations.limit_used", pct=f"{limit.get('percentage', 0):.1f}"), size=12, muted=True),
                    mei_text(
                        t(
                            "mei.obligations.limit_projection",
                            date=limit["projected_limit_date"].strftime("%d/%m/%Y"),
                        )
                        if limit.get("projected_limit_date")
                        else t("mei.obligations.limit_no_projection"),
                        size=12,
                        muted=True,
                    ),
                ],
                spacing=8,
            ),
            expand=True,
        )

        migration_card = ft.Container()
        if limit.get("percentage", 0) >= ME_MIGRATION_THRESHOLD_PCT:
            sim = simulate_me_migration(
                ytd_revenue=limit.get("ytd_revenue", 0),
                projected_annual=limit.get("projected_annual", 0),
                activity_type=ctx.activity_type,
                custom_das=float(ctx.custom_das_amount) if ctx.custom_das_amount else None,
                annual_limit=limit.get("annual_limit"),
            )
            rec_key = f"mei.migration.{sim['recommendation']}"
            rec_label = t(rec_key)
            if rec_label == rec_key:
                rec_label = sim["recommendation"]
            migration_card = mei_card(
                ft.Column(
                    [
                        mei_heading(t("mei.obligations.migration_heading"), size=16),
                        mei_text(
                            t(
                                "mei.obligations.migration_taxes",
                                mei=format_brl(sim["mei_annual_tax"]),
                                simples=format_brl(sim["simples_annual_tax_projected"]),
                            ),
                            size=12,
                        ),
                        ft.Text(rec_label, size=13, color=MEI_ACCENT),
                        mei_text(t("mei.migration.disclaimer"), size=10, muted=True, italic=True),
                    ],
                    spacing=6,
                ),
                bgcolor=tc.surface_alt,
                border=ft.Border.all(1, MEI_ACCENT),
                padding=20,
            )

        check_items = []
        for item in checklist:
            icon = ft.Icons.CHECK_CIRCLE if item["done"] else (ft.Icons.WARNING if item.get("urgent") else ft.Icons.RADIO_BUTTON_UNCHECKED)
            color = theme_colors().success if item["done"] else (theme_colors().danger if item.get("urgent") else tc.text_muted)
            check_items.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, color=color, size=22),
                            ft.Column(
                                [
                                    ft.Text(item["label"], color=tc.text_primary, size=13),
                                    mei_text(item.get("hint", ""), size=10, muted=True),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=ft.Padding(left=4, top=8, right=4, bottom=8),
                )
            )

        today = date.today()
        month_label = t(f"mei.month.{today.month}")
        return ft.Column(
            [
                header,
                ft.Container(height=16),
                ft.Row([das_card, limit_card], spacing=16),
                ft.Container(height=16),
                migration_card,
                ft.Container(height=16) if limit.get("percentage", 0) >= ME_MIGRATION_THRESHOLD_PCT else ft.Container(),
                section_card(
                    t("mei.obligations.checklist", month=month_label, year=today.year),
                    ft.Column(check_items, spacing=4),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _confirm_das(self, _):
        confirm_das_for_context(self.app, self.ctx)

    def _export_das_calendar(self, _):
        try:
            path = export_das_ics(self.ctx.profile_id)
            self.app.show_snack(t("mei.obligations.ics_saved", path=path))
        except Exception as ex:
            self.app.show_snack(t("mei.obligations.ics_error", error=ex), success=False)
