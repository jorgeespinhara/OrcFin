"""MEI light inventory — products and stock."""

from __future__ import annotations

import flet as ft

from core.copy import EMPTY_CELL
from core.domain.value_objects.money import format_brl
from core.mei_inventory_summary import get_inventory_summary
from core.mei_operational import enabled_modules
from ui.mei.components import mei_text, mei_title, metric_card, section_card
from ui.mei.constants import MEI_ACCENT
from ui.mei.context import MeiContext, require_mei_ready
from ui.mei.inventory_actions import open_movement_modal, open_product_modal
from ui.theme import active as theme_colors


class MeiEstoqueView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup
        if "inventory" not in enabled_modules(self.ctx.operational_profile):
            return mei_text("Estoque disponível para perfis Vendas e cobrança ou Misto.", size=14)

        pid = self.ctx.profile_id
        summary = get_inventory_summary(pid)
        tc = theme_colors()

        header = ft.Row(
            [
                mei_title("Estoque"),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Novo produto",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_product_modal(self.app, pid),
                    style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                ),
            ],
        )

        kpis = ft.Row(
            [
                metric_card("Produtos", str(summary["product_count"]), "#6366F1", ft.Icons.INVENTORY),
                metric_card("Estoque baixo", str(summary["low_stock_count"]), "#F97316", ft.Icons.WARNING),
                metric_card("Valor em estoque", format_brl(summary["stock_value"]), "#22C55E", ft.Icons.SAVINGS),
            ],
            spacing=12,
            wrap=True,
        )

        if not summary["products"]:
            body = section_card(mei_text("Nenhum produto cadastrado. Comece pelo cadastro e movimentações de entrada.", size=13))
            return ft.Column([header, ft.Container(height=8), kpis, ft.Container(height=12), body], expand=True)

        rows = []
        for product in summary["products"]:
            pid_prod = int(product["id"])
            qty = float(product.get("stock_qty") or 0)
            threshold = product.get("low_stock_threshold")
            low = threshold is not None and qty <= float(threshold)
            detail = [
                ft.Text(product["name"], size=14, weight=ft.FontWeight.W_600, color=tc.text_primary),
                mei_text(
                    f"SKU {product.get('sku') or EMPTY_CELL} · {qty:g} un · venda {format_brl(product.get('unit_price') or 0)}",
                    size=12,
                    muted=True,
                ),
            ]
            if low:
                detail.append(mei_text("Estoque baixo", size=12, color="#F97316"))
            actions = ft.Row(
                [
                    ft.TextButton("Entrada", on_click=lambda _, p=pid_prod: open_movement_modal(self.app, pid, p, "in")),
                    ft.TextButton("Saída", on_click=lambda _, p=pid_prod: open_movement_modal(self.app, pid, p, "out")),
                    ft.TextButton("Ajustar", on_click=lambda _, p=pid_prod: open_movement_modal(self.app, pid, p, "adjust")),
                ],
                spacing=4,
            )
            rows.append(section_card(ft.Column([*detail, actions], spacing=6, tight=True)))

        return ft.Column(
            [header, ft.Container(height=8), kpis, ft.Container(height=12), *rows],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )