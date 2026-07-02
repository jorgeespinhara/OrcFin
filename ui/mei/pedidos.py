"""MEI work orders and outsourcing lines."""

from __future__ import annotations

from datetime import date

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.mei import get_mei_clients
from core.db.repositories.mei_orders import get_orders, get_outsource_for_order
from core.domain.value_objects.money import format_brl
from core.mei_operational import enabled_modules
from ui.mei.components import mei_text, mei_title, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.mei.order_actions import confirm_order_done, open_order_modal, open_outsource_modal
from ui.theme import active as theme_colors


class MeiPedidosView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup
        if "orders" not in enabled_modules(self.ctx.operational_profile):
            return mei_text("Pedidos disponível para perfis Serviço por pedido ou Misto.", size=14)

        pid = self.ctx.profile_id
        today = date.today()
        orders = get_orders(pid, year=today.year, month=today.month)
        clients = {c.id: c.name for c in get_mei_clients(pid)}
        tc = theme_colors()

        header = ft.Row(
            [
                mei_title("Pedidos do mês"),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Novo pedido",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_order_modal(self.app, pid),
                    style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                ),
            ],
        )

        if not orders:
            body = section_card(mei_text("Nenhum pedido neste mês. Registre recebimentos e terceirizações por pedido.", size=13))
            return ft.Column([header, ft.Container(height=8), body], expand=True)

        rows = []
        for order in orders:
            oid = int(order["id"])
            lines = get_outsource_for_order(oid)
            client_name = clients.get(order.get("client_id")) or EMPTY_CELL
            cost = sum(float(l["amount"]) for l in lines)
            status = "Concluído" if order.get("status") == "done" else "Aberto"
            detail = [
                ft.Text(
                    f"{order['reference']} · {client_name} · {format_brl(order['revenue_amount'])}",
                    size=13,
                    color=tc.text_primary,
                ),
                mei_text(
                    f"{order['order_date']} · {status} · custo terceiros {format_brl(cost)}",
                    size=12,
                    muted=True,
                ),
            ]
            actions = ft.Row(
                [
                    ft.TextButton(
                        "Terceirizar",
                        on_click=lambda _, o=oid: open_outsource_modal(self.app, pid, o),
                    ),
                ]
                + (
                    [ft.TextButton("Concluir", on_click=lambda _, o=oid: confirm_order_done(self.app, o))]
                    if order.get("status") != "done"
                    else []
                ),
                spacing=4,
            )
            if lines:
                for line in lines:
                    paid = "pago" if line.get("paid_at") else "a pagar"
                    detail.append(
                        mei_text(
                            f"  → {line['supplier_name']}: {format_brl(line['amount'])} ({paid})",
                            size=12,
                            muted=True,
                        )
                    )
            rows.append(section_card(ft.Column([*detail, actions], spacing=6, tight=True)))

        return ft.Column([header, ft.Container(height=8), *rows], scroll=ft.ScrollMode.AUTO, expand=True)