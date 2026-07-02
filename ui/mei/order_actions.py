"""Modals for MEI orders and suppliers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.mei import get_mei_clients
from core.db.repositories.mei_orders import (
    add_outsource,
    create_order,
    create_supplier,
    get_suppliers,
    mark_order_done,
    pay_outsource_line,
)
from core.models import MeiOrder, MeiOrderOutsource, MeiSupplier
from ui.mei.components import modal_actions, modal_dropdown, modal_field
from ui.mei.constants import MEI_ACCENT


def open_supplier_modal(app: "OrcFinApp", profile_id: int):
    name_f = modal_field(label="Nome do terceiro", width=360)
    doc_f = modal_field(label="CPF/CNPJ (opcional)", width=360)

    def save(_):
        if not name_f.value:
            return
        create_supplier(MeiSupplier(profile_id=profile_id, name=name_f.value, document=doc_f.value))
        app.close_modal()
        app.show_snack("Terceiro cadastrado")
        app.refresh_current_view()

    app.show_modal(
        ft.Column([name_f, doc_f, modal_actions(app, "Salvar", save)], spacing=12, tight=True),
        title="Novo terceiro",
    )


def open_order_modal(app: "OrcFinApp", profile_id: int):
    clients = get_mei_clients(profile_id)
    ref_f = modal_field(label="Referência do pedido", width=360)
    revenue_f = modal_field(label="Valor cobrado (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    date_f = modal_field(label="Data", value=date.today().isoformat(), width=360)
    notes_f = modal_field(label="Observações", width=360)
    client_dd = modal_dropdown(
        label="Cliente",
        width=360,
        options=[ft.dropdown.Option("", EMPTY_CELL)] + [ft.dropdown.Option(str(c.id), c.name) for c in clients],
    )

    def save(_):
        if not ref_f.value:
            app.show_snack("Informe a referência do pedido", success=False)
            return
        try:
            revenue = Decimal(revenue_f.value.replace(",", "."))
            order_date = date.fromisoformat(date_f.value)
        except Exception:
            app.show_snack("Dados inválidos", success=False)
            return
        client_id = int(client_dd.value) if client_dd.value else None
        create_order(
            MeiOrder(
                profile_id=profile_id,
                client_id=client_id,
                reference=ref_f.value,
                revenue_amount=revenue,
                order_date=order_date,
                notes=notes_f.value,
            )
        )
        app.close_modal()
        app.show_snack("Pedido registrado")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [ref_f, revenue_f, date_f, client_dd, notes_f, modal_actions(app, "Salvar", save)],
            spacing=12,
            tight=True,
        ),
        title="Novo pedido",
    )


def open_outsource_modal(app: "OrcFinApp", profile_id: int, order_id: int):
    suppliers = get_suppliers(profile_id)
    if not suppliers:
        app.show_snack("Cadastre um terceiro antes", success=False)
        return
    amount_f = modal_field(label="Valor a pagar (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    sent_f = modal_field(label="Data envio (AAAA-MM-DD)", value=date.today().isoformat(), width=360)
    notes_f = modal_field(label="Observações", width=360)
    supplier_dd = modal_dropdown(
        label="Terceiro",
        width=360,
        options=[ft.dropdown.Option(str(s.id), s.name) for s in suppliers],
    )

    def save(_):
        try:
            amount = Decimal(amount_f.value.replace(",", "."))
            sent = date.fromisoformat(sent_f.value) if sent_f.value else None
            supplier_id = int(supplier_dd.value)
        except Exception:
            app.show_snack("Dados inválidos", success=False)
            return
        add_outsource(
            MeiOrderOutsource(
                order_id=order_id,
                supplier_id=supplier_id,
                amount=amount,
                sent_date=sent,
                notes=notes_f.value,
            )
        )
        app.close_modal()
        app.show_snack("Terceirização registrada")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [supplier_dd, amount_f, sent_f, notes_f, modal_actions(app, "Salvar", save)],
            spacing=12,
            tight=True,
        ),
        title="Terceirizar pedido",
    )


def confirm_pay_outsource(app: "OrcFinApp", profile_id: int, line_id: int):
    tx_id = pay_outsource_line(profile_id, line_id)
    app.show_snack("Pagamento registrado" if tx_id else "Não foi possível registrar", success=bool(tx_id))
    app.refresh_current_view()


def confirm_order_done(app: "OrcFinApp", order_id: int):
    if mark_order_done(order_id):
        app.show_snack("Pedido concluído")
        app.refresh_current_view()