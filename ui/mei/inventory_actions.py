"""Modals for MEI light inventory."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.db.repositories.mei_inventory import create_product, record_movement
from core.models import MeiProduct, MeiStockMovement
from ui.mei.components import modal_actions, modal_field


def open_product_modal(app: "OrcFinApp", profile_id: int):
    name_f = modal_field(label="Nome do produto", width=360)
    sku_f = modal_field(label="SKU (opcional)", width=360)
    price_f = modal_field(label="Preço de venda (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    cost_f = modal_field(label="Custo unitário (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    stock_f = modal_field(label="Estoque inicial", value="0", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    low_f = modal_field(label="Alerta estoque baixo", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    notes_f = modal_field(label="Observações", width=360)

    def save(_):
        if not name_f.value:
            app.show_snack("Informe o nome do produto", success=False)
            return
        try:
            unit_price = Decimal(price_f.value.replace(",", ".") or "0")
            cost_price = Decimal(cost_f.value.replace(",", ".")) if cost_f.value else None
            stock_qty = Decimal(stock_f.value.replace(",", ".") or "0")
            low = Decimal(low_f.value.replace(",", ".")) if low_f.value else None
        except Exception:
            app.show_snack("Dados inválidos", success=False)
            return
        create_product(
            MeiProduct(
                profile_id=profile_id,
                name=name_f.value,
                sku=sku_f.value or None,
                unit_price=unit_price,
                cost_price=cost_price,
                stock_qty=stock_qty,
                low_stock_threshold=low,
                notes=notes_f.value,
            )
        )
        app.close_modal()
        app.show_snack("Produto cadastrado")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [name_f, sku_f, price_f, cost_f, stock_f, low_f, notes_f, modal_actions(app, "Salvar", save)],
            spacing=12,
            tight=True,
        ),
        title="Novo produto",
    )


def open_movement_modal(app: "OrcFinApp", profile_id: int, product_id: int, movement_type: str):
    from core.db.repositories.mei_inventory import get_product

    product = get_product(product_id)
    if not product:
        return

    labels = {"in": "Entrada", "out": "Saída", "adjust": "Ajuste de estoque"}
    qty_f = modal_field(
        label="Quantidade" if movement_type != "adjust" else "Nova quantidade em estoque",
        width=360,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    date_f = modal_field(label="Data", value=date.today().isoformat(), width=360)
    cost_f = modal_field(label="Custo unitário (opcional)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    notes_f = modal_field(label="Observações", width=360)
    expense_cb = ft.Checkbox(label="Registrar despesa de compra", value=movement_type == "in")

    def save(_):
        try:
            qty = Decimal(qty_f.value.replace(",", "."))
            mov_date = date.fromisoformat(date_f.value)
            unit_cost = Decimal(cost_f.value.replace(",", ".")) if cost_f.value else None
        except Exception:
            app.show_snack("Dados inválidos", success=False)
            return
        result = record_movement(
            MeiStockMovement(
                product_id=product_id,
                movement_type=movement_type,  # type: ignore[arg-type]
                quantity=qty,
                unit_cost=unit_cost,
                movement_date=mov_date,
                notes=notes_f.value,
            ),
            profile_id=profile_id,
            create_purchase_expense=bool(expense_cb.value),
        )
        if not result:
            app.show_snack("Movimento inválido ou estoque insuficiente", success=False)
            return
        app.close_modal()
        app.show_snack("Estoque atualizado")
        app.refresh_current_view()

    controls = [qty_f, date_f, notes_f]
    if movement_type == "in":
        controls.insert(2, cost_f)
        controls.append(expense_cb)

    app.show_modal(
        ft.Column([*controls, modal_actions(app, "Salvar", save)], spacing=12, tight=True),
        title=f"{labels.get(movement_type, 'Movimento')} · {product.get('name', '')}",
    )