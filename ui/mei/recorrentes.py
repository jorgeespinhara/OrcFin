"""MEI recurring subscriptions and monthly charges."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.copy import EMPTY_CELL
from core.domain.value_objects.money import format_brl
from core.i18n import t
from core.mei_operational import enabled_modules
from core.mei_recurring_billing import get_monthly_recurring_summary
from core.db.repositories.mei_recurring import get_subscriptions
from ui.mei.components import mei_text, mei_title, metric_card, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.mei.recurring_actions import (
    confirm_cancel_subscription,
    confirm_pause_subscription,
    confirm_receive_charge,
    open_subscription_modal,
)
from ui.theme import active as theme_colors, primary_button_style


class MeiRecorrentesView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup
        if "recurring_billing" not in enabled_modules(self.ctx.operational_profile):
            return mei_text(t("mei.recurring.unavailable"), size=14)

        pid = self.ctx.profile_id
        today = date.today()
        summary = get_monthly_recurring_summary(pid, today.year, today.month)
        subs = get_subscriptions(pid)
        tc = theme_colors()

        header = ft.Row(
            [
                mei_title(t("mei.recurring.title")),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    t("mei.recurring.new_contract"),
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_subscription_modal(self.app, pid),
                    style=primary_button_style(bgcolor=MEI_ACCENT),
                ),
            ],
        )

        kpis = ft.Row(
            [
                metric_card(t("mei.recurring.kpi_contracts"), str(len(subs)), theme_colors().accent_portfolio, ft.Icons.REPEAT),
                metric_card(t("mei.recurring.kpi_charges"), str(summary["charge_count"]), MEI_ACCENT, ft.Icons.CALENDAR_MONTH),
                metric_card(t("mei.recurring.kpi_pending"), format_brl(summary["pending_total"]), theme_colors().expense, ft.Icons.PAYMENTS),
                metric_card(t("mei.recurring.kpi_received"), format_brl(summary["received_total"]), theme_colors().success, ft.Icons.CHECK_CIRCLE),
            ],
            spacing=12,
            wrap=True,
        )

        charge_blocks = []
        for charge in summary["charges"]:
            cid = int(charge["id"])
            paid = bool(charge.get("paid_at"))
            client = charge.get("client_name") or EMPTY_CELL
            status = t("mei.recurring.status_received") if paid else t("mei.recurring.status_pending")
            actions = []
            if not paid:
                actions.append(
                    ft.TextButton(
                        t("mei.recurring.receive"),
                        on_click=lambda _, i=cid: confirm_receive_charge(self.app, pid, i),
                    )
                )
            charge_blocks.append(
                section_card(
                    ft.Column(
                        [
                            ft.Text(
                                f"{charge['subscription_name']} · {client} · {format_brl(charge['amount'])}",
                                size=13,
                                color=tc.text_primary,
                            ),
                            mei_text(
                                t("mei.recurring.due_status", date=charge["due_date"], status=status),
                                size=12,
                                muted=True,
                            ),
                            ft.Row(actions, spacing=4) if actions else ft.Container(),
                        ],
                        spacing=6,
                        tight=True,
                    )
                )
            )

        if not charge_blocks:
            charge_blocks.append(
                section_card(mei_text(t("mei.recurring.empty_charges"), size=13))
            )

        contract_blocks = []
        status_map = {
            "active": t("mei.recurring.status_active"),
            "paused": t("mei.recurring.status_paused"),
            "cancelled": t("mei.recurring.status_cancelled"),
        }
        for sub in subs:
            sid = int(sub["id"])
            status_label = status_map.get(sub.get("status"), sub.get("status"))
            actions = []
            if sub.get("status") == "active":
                actions = [
                    ft.TextButton(t("mei.recurring.pause"), on_click=lambda _, i=sid: confirm_pause_subscription(self.app, i)),
                    ft.TextButton(t("mei.recurring.cancel"), on_click=lambda _, i=sid: confirm_cancel_subscription(self.app, i)),
                ]
            contract_blocks.append(
                section_card(
                    ft.Column(
                        [
                            ft.Text(sub["name"], size=14, weight=ft.FontWeight.W_600, color=tc.text_primary),
                            mei_text(
                                t(
                                    "mei.recurring.contract_meta",
                                    amount=format_brl(sub["monthly_amount"]),
                                    day=sub["due_day"],
                                    status=status_label,
                                ),
                                size=12,
                                muted=True,
                            ),
                            ft.Row(actions, spacing=4) if actions else ft.Container(),
                        ],
                        spacing=6,
                        tight=True,
                    )
                )
            )

        return ft.Column(
            [
                header,
                ft.Container(height=8),
                kpis,
                ft.Container(height=12),
                mei_title(t("mei.recurring.charges_month"), size=18),
                *charge_blocks,
                ft.Container(height=8),
                mei_title(t("mei.recurring.contracts"), size=18),
                *contract_blocks,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
