"""Transaction row actions — edit, delete, and transfer."""

from __future__ import annotations

import flet as ft

from decimal import Decimal
from core.models import Transaction, TransactionType
from core.db.repositories.transactions import create_internal_transfer, delete_transactions_batch, split_transaction
from ui.transactions.form import show_transaction_form

def open_new_transaction_modal(view, e):
    """Open the professional transaction entry modal."""
    show_transaction_form(view)

def edit_transaction(view, tx: Transaction):
    if tx.id is None:
        return
    show_transaction_form(view, existing_tx=tx)

def open_split_modal(view, tx: Transaction):
    if tx.id is None:
        return
    cats = [c for c in view.categories if c.type == tx.type]
    if len(cats) < 2:
        view.app.show_snack("Cadastre ao menos 2 categorias do mesmo tipo", success=False)
        return
    amt1 = ft.TextField(label="Valor parte 1", value=str(tx.amount / 2), keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    cat1 = ft.Dropdown(label="Categoria 1", options=[ft.dropdown.Option(str(c.id), c.name) for c in cats], value=str(cats[0].id), expand=True)
    cat2 = ft.Dropdown(label="Categoria 2", options=[ft.dropdown.Option(str(c.id), c.name) for c in cats], value=str(cats[1].id), expand=True)

    def save(_):
        try:
            a1 = Decimal((amt1.value or "0").replace(",", "."))
            a2 = tx.amount - a1
            if a1 <= 0 or a2 <= 0:
                raise ValueError("valores inválidos")
            split_transaction(tx.id, [(int(cat1.value), a1), (int(cat2.value), a2)])
            view.app.close_modal()
            view.app.show_snack("Lançamento dividido")
            view.app.refresh_current_view()
        except Exception as ex:
            view.app.show_snack(f"Erro: {ex}", success=False)

    view.app.show_modal(
        ft.Column([amt1, ft.Row([cat1, cat2], spacing=8), ft.ElevatedButton("Dividir", on_click=save)], spacing=12, tight=True),
        title=f"Dividir lançamento: {tx.description[:30]}",
    )

def open_transfer_modal(view, tx: Transaction):
    if tx.id is None:
        return
    if view.app.is_consolidated:
        view.app.show_snack("Transferência só na visão individual", success=False)
        return
    others = [p for p in view.profiles if p.id != tx.profile_id]
    if not others:
        view.app.show_snack("Cadastre outro perfil", success=False)
        return
    to_dd = ft.Dropdown(label="Para perfil", options=[ft.dropdown.Option(str(p.id), p.name) for p in others], value=str(others[0].id))

    def save(_):
        try:
            from core.db.repositories.categories import get_categories_for_profile
            dest = int(to_dd.value)
            inc = next(c for c in get_categories_for_profile(dest) if c.type == TransactionType.INCOME)
            create_internal_transfer(
                tx.profile_id,
                dest,
                tx.amount,
                f"Transferência: {tx.description[:40]}",
                tx.date,
                tx.category_id,
                inc.id,
            )
            delete_transactions_batch([tx.id])
            view.app.close_modal()
            view.app.show_snack("Transferência registrada")
            view.app.refresh_current_view()
        except Exception as ex:
            view.app.show_snack(f"Erro: {ex}", success=False)

    view.app.show_modal(ft.Column([to_dd, ft.ElevatedButton("Transferir", on_click=save)], spacing=12, tight=True), title="Transferir entre perfis")

def import_statement(view, _):
    from ui.import_flow import open_import_flow

    open_import_flow(view.app)
