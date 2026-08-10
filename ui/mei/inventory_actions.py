"""Modals for MEI light inventory."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.db.repositories.mei_inventory import create_product, record_movement
from core.i18n import t
from core.models import MeiProduct, MeiStockMovement
from ui.mei.components import modal_actions, modal_field


def open_product_modal(app: "OrcFinApp", profile_id: int):
    name_f = modal_field(label=t("mei.inventory.product_name"), width=360)
    sku_f = modal_field(label=t("mei.inventory.sku"), width=360)
    price_f = modal_field(label=t("mei.inventory.sale_price"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
    cost_f = modal_field(label=t("mei.inventory.unit_cost"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
    stock_f = modal_field(label=t("mei.inventory.initial_stock"), value="0", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    low_f = modal_field(label=t("mei.inventory.low_alert"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
    notes_f = modal_field(label=t("mei.inventory.notes"), width=360)

    def save(_):
        if not name_f.value:
            app.show_snack(t("mei.inventory.need_name"), success=False)
            return
        try:
            unit_price = Decimal(price_f.value.replace(",", ".") or "0")
            cost_price = Decimal(cost_f.value.replace(",", ".")) if cost_f.value else None
            stock_qty = Decimal(stock_f.value.replace(",", ".") or "0")
            low = Decimal(low_f.value.replace(",", ".")) if low_f.value else None
        except Exception:
            app.show_snack(t("mei.inventory.invalid"), success=False)
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
        app.show_snack(t("mei.inventory.product_saved"))
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [name_f, sku_f, price_f, cost_f, stock_f, low_f, notes_f, modal_actions(app, t("common.save"), save)],
            spacing=12,
            tight=True,
        ),
        title=t("mei.inventory.product_new_title"),
    )


def open_movement_modal(app: "OrcFinApp", profile_id: int, product_id: int, movement_type: str):
    from core.db.repositories.mei_inventory import get_product

    product = get_product(product_id)
    if not product:
        return

    labels = {
        "in": t("mei.inventory.mov_in"),
        "out": t("mei.inventory.mov_out"),
        "adjust": t("mei.inventory.mov_adjust"),
    }
    qty_f = modal_field(
        label=t("mei.inventory.mov_qty") if movement_type != "adjust" else t("mei.inventory.mov_new_qty"),
        width=360,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    date_f = modal_field(label=t("mei.inventory.mov_date"), value=date.today().isoformat(), width=360)
    cost_f = modal_field(label=t("mei.inventory.mov_cost_opt"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
    notes_f = modal_field(label=t("mei.inventory.notes"), width=360)
    expense_cb = ft.Checkbox(label=t("mei.inventory.mov_expense"), value=movement_type == "in")

    def save(_):
        try:
            qty = Decimal(qty_f.value.replace(",", "."))
            mov_date = date.fromisoformat(date_f.value)
            unit_cost = Decimal(cost_f.value.replace(",", ".")) if cost_f.value else None
        except Exception:
            app.show_snack(t("mei.inventory.invalid"), success=False)
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
            app.show_snack(t("mei.inventory.mov_fail"), success=False)
            return
        app.close_modal()
        app.show_snack(t("mei.inventory.updated"))
        app.refresh_current_view()

    controls = [qty_f, date_f, notes_f]
    if movement_type == "in":
        controls.insert(2, cost_f)
        controls.append(expense_cb)

    app.show_modal(
        ft.Column([*controls, modal_actions(app, t("common.save"), save)], spacing=12, tight=True),
        title=t(
            "mei.inventory.mov_title",
            kind=labels.get(movement_type, t("mei.inventory.mov_generic")),
            name=product.get("name", ""),
        ),
    )
