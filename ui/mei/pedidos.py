"""MEI work orders and outsourcing lines."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.mei import get_mei_clients
from core.db.repositories.mei_orders import get_orders, get_outsource_for_order
from core.domain.value_objects.money import format_brl
from core.i18n import t
from core.mei_operational import enabled_modules
from ui.mei.components import mei_text, mei_title, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.mei.order_actions import confirm_order_done, open_order_modal, open_outsource_modal
from ui.theme import active as theme_colors, primary_button_style


class MeiPedidosView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup
        if "orders" not in enabled_modules(self.ctx.operational_profile):
            return mei_text(t("mei.orders.unavailable"), size=14)

        pid = self.ctx.profile_id
        today = date.today()
        orders = get_orders(pid, year=today.year, month=today.month)
        clients = {c.id: c.name for c in get_mei_clients(pid)}
        tc = theme_colors()

        header = ft.Row(
            [
                mei_title(t("mei.orders.title")),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    t("mei.orders.new"),
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_order_modal(self.app, pid),
                    style=primary_button_style(bgcolor=MEI_ACCENT),
                ),
            ],
        )

        if not orders:
            body = section_card(mei_text(t("mei.orders.empty"), size=13))
            return ft.Column([header, ft.Container(height=8), body], expand=True)

        rows = []
        for order in orders:
            oid = int(order["id"])
            lines = get_outsource_for_order(oid)
            client_name = clients.get(order.get("client_id")) or EMPTY_CELL
            cost = sum(float(l["amount"]) for l in lines)
            status = t("mei.orders.status_done") if order.get("status") == "done" else t("mei.orders.status_open")
            detail = [
                ft.Text(
                    f"{order['reference']} · {client_name} · {format_brl(order['revenue_amount'])}",
                    size=13,
                    color=tc.text_primary,
                ),
                mei_text(
                    t(
                        "mei.orders.line_meta",
                        date=order["order_date"],
                        status=status,
                        cost=format_brl(cost),
                    ),
                    size=12,
                    muted=True,
                ),
            ]
            actions = ft.Row(
                [
                    ft.TextButton(
                        t("mei.orders.outsource"),
                        on_click=lambda _, o=oid: open_outsource_modal(self.app, pid, o),
                    ),
                ]
                + (
                    [ft.TextButton(t("mei.orders.complete"), on_click=lambda _, o=oid: confirm_order_done(self.app, o))]
                    if order.get("status") != "done"
                    else []
                ),
                spacing=4,
            )
            if lines:
                for line in lines:
                    paid = t("mei.orders.paid") if line.get("paid_at") else t("mei.orders.to_pay")
                    detail.append(
                        mei_text(
                            t(
                                "mei.orders.supplier_line",
                                name=line["supplier_name"],
                                amount=format_brl(line["amount"]),
                                status=paid,
                            ),
                            size=12,
                            muted=True,
                        )
                    )
            rows.append(section_card(ft.Column([*detail, actions], spacing=6, tight=True)))

        return ft.Column([header, ft.Container(height=8), *rows], scroll=ft.ScrollMode.AUTO, expand=True)
