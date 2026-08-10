"""MEI third-party payables — monthly consolidation."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.domain.value_objects.money import format_brl
from core.i18n import t
from core.mei_operational import enabled_modules
from core.mei_payables import get_monthly_payables_summary
from ui.mei.components import mei_text, mei_title, metric_card, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.mei.order_actions import confirm_pay_outsource, open_supplier_modal
from ui.theme import active as theme_colors


class MeiPayablesView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup
        if "orders" not in enabled_modules(self.ctx.operational_profile):
            return mei_text(t("mei.payables.unavailable"), size=14)

        pid = self.ctx.profile_id
        today = date.today()
        summary = get_monthly_payables_summary(pid, today.year, today.month)

        header = ft.Row(
            [
                mei_title(t("mei.payables.title")),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    t("mei.payables.new_supplier"),
                    icon=ft.Icons.PERSON_ADD,
                    on_click=lambda _: open_supplier_modal(self.app, pid),
                ),
            ],
        )

        kpis = ft.Row(
            [
                metric_card(t("mei.payables.kpi_orders"), str(summary["order_count"]), theme_colors().accent_portfolio, ft.Icons.INVENTORY_2),
                metric_card(t("mei.payables.kpi_outsourced"), str(summary["outsourced_count"]), MEI_ACCENT, ft.Icons.ENGINEERING),
                metric_card(t("mei.payables.kpi_payable"), format_brl(summary["payable_total"]), theme_colors().expense, ft.Icons.PAYMENTS),
                metric_card(t("mei.payables.kpi_margin"), format_brl(summary["margin_estimate"]), theme_colors().success, ft.Icons.TRENDING_UP),
            ],
            spacing=12,
            wrap=True,
        )

        supplier_blocks = []
        for bucket in summary["by_supplier"]:
            lines_ui = []
            for line in bucket["lines"]:
                lid = int(line["line_id"])
                lines_ui.append(
                    ft.Row(
                        [
                            mei_text(
                                f"{line['reference']} · {format_brl(line['amount'])}",
                                size=12,
                            ),
                            ft.TextButton(
                                t("mei.payables.record_payment"),
                                on_click=lambda _, i=lid: confirm_pay_outsource(self.app, pid, i),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
            supplier_blocks.append(
                section_card(
                    ft.Column(
                        [
                            ft.Text(bucket["supplier_name"], size=14, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                            mei_text(t("mei.payables.open_total", amount=format_brl(bucket["total"])), size=12, muted=True),
                            *lines_ui,
                        ],
                        spacing=6,
                        tight=True,
                    )
                )
            )

        if not supplier_blocks:
            supplier_blocks.append(
                section_card(mei_text(t("mei.payables.empty"), size=13))
            )

        return ft.Column(
            [header, ft.Container(height=8), kpis, ft.Container(height=12), *supplier_blocks],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
