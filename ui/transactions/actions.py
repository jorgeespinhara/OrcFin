"""Transaction row actions — edit, delete, and transfer."""

from __future__ import annotations

from decimal import Decimal

import flet as ft

from core.db.repositories.categories import display_name
from core.db.repositories.transactions import (
    create_internal_transfer,
    delete_transactions_batch,
    split_transaction,
)
from core.i18n import t
from core.models import Transaction, TransactionType
from ui.theme import (
    active as theme_colors,
    on_surface_button_style,
    primary_button_style,
)
from ui.transactions.form import show_transaction_form


def open_new_transaction_modal(view, e=None):
    show_transaction_form(view)


def edit_transaction(view, tx: Transaction):
    if tx.id is None:
        return
    show_transaction_form(view, existing_tx=tx)


def open_split_modal(view, tx: Transaction):
    if tx.id is None:
        return
    c = theme_colors()
    cats = [cat for cat in view.categories if cat.type == tx.type]
    if len(cats) < 2:
        view.app.show_snack(t("tx.actions.split_need_cats"), success=False)
        return
    amt1 = ft.TextField(
        label=t("tx.actions.split_amount1"),
        value=str(tx.amount / 2).replace(".", ","),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    cat1 = ft.Dropdown(
        label=t("tx.actions.split_cat1"),
        options=[ft.dropdown.Option(str(cat.id), display_name(cat)) for cat in cats],
        value=str(cats[0].id),
        expand=True,
    )
    cat2 = ft.Dropdown(
        label=t("tx.actions.split_cat2"),
        options=[ft.dropdown.Option(str(cat.id), display_name(cat)) for cat in cats],
        value=str(cats[1].id),
        expand=True,
    )

    def save(_):
        try:
            from ui.transactions.data import parse_brl_amount

            a1 = parse_brl_amount(amt1.value)
            a2 = tx.amount - a1
            if a1 <= 0 or a2 <= 0:
                raise ValueError(t("tx.actions.split_invalid"))
            split_transaction(tx.id, [(int(cat1.value), a1), (int(cat2.value), a2)])
            view.app.close_modal()
            view.app.show_snack(t("tx.actions.split_done"))
            view.app.refresh_current_view()
        except Exception as ex:
            view.app.show_snack(t("common.error", error=ex), success=False)

    view.app.show_modal(
        ft.Column(
            [
                ft.Text(
                    t("tx.actions.split_hint", amount=tx.amount),
                    size=12,
                    color=c.text_muted,
                ),
                amt1,
                ft.Row([cat1, cat2], spacing=8),
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"),
                            on_click=lambda _: view.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        ft.ElevatedButton(t("tx.split"), on_click=save, style=primary_button_style()),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title=t("tx.split"),
    )


def open_transfer_modal(view, tx: Transaction):
    if tx.id is None:
        return
    c = theme_colors()
    if view.app.is_consolidated:
        view.app.show_snack(t("tx.actions.transfer_individual"), success=False)
        return
    others = [p for p in view.profiles if p.id != tx.profile_id]
    if not others:
        view.app.show_snack(t("tx.actions.transfer_need_profile"), success=False)
        return
    to_dd = ft.Dropdown(
        label=t("tx.actions.transfer_to"),
        options=[ft.dropdown.Option(str(p.id), p.name) for p in others],
        value=str(others[0].id),
        expand=True,
    )

    def save(_):
        try:
            from core.db.repositories.categories import get_categories_for_profile

            dest = int(to_dd.value)
            inc = next(cat for cat in get_categories_for_profile(dest) if cat.type == TransactionType.INCOME)
            create_internal_transfer(
                tx.profile_id,
                dest,
                tx.amount,
                t("tx.actions.transfer_desc", description=tx.description),
                tx.date,
                tx.category_id,
                inc.id,
            )
            delete_transactions_batch([tx.id])
            view.app.close_modal()
            view.app.show_snack(t("tx.actions.transfer_done"))
            view.app.refresh_current_view()
        except Exception as ex:
            view.app.show_snack(t("common.error", error=ex), success=False)

    view.app.show_modal(
        ft.Column(
            [
                ft.Text(
                    t("tx.actions.transfer_hint", amount=tx.amount, description=tx.description),
                    size=12,
                    color=c.text_muted,
                ),
                to_dd,
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"),
                            on_click=lambda _: view.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        ft.ElevatedButton(t("tx.transfer"), on_click=save, style=primary_button_style()),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title=t("tx.actions.transfer_title"),
    )


def import_statement(view, _=None):
    from ui.import_flow import open_import_flow

    open_import_flow(view.app)
