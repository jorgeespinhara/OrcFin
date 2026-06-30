"""MEI modals and row actions."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import flet as ft

from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.mei import (
    create_mei_client,
    create_mei_invoice,
    delete_mei_client,
    delete_mei_invoice,
    get_mei_clients,
    update_mei_config,
)
from core.db.repositories.transactions import create_transaction
from core.models import MeiClient, MeiInvoice, MeiConfig, Transaction, TransactionType
from ui.mei.components import modal_dropdown, modal_field
from ui.mei.constants import ACTIVITY_LABELS, MEI_ACCENT
from ui.mei.context import MeiContext


def confirm_das_for_context(app: "OrcFinApp", ctx: MeiContext) -> None:
    from core.services.mei_service import confirm_das_payment

    tx_id = confirm_das_payment(ctx.profile_id, date.today(), ctx.das_amount)
    app.show_snack("DAS registrado" if tx_id else "DAS já registrado", success=bool(tx_id))
    app.refresh_current_view()


def open_edit_config(app: "OrcFinApp"):
    ctx = MeiContext.load()
    if not ctx.is_ready:
        return
    razao_f = modal_field(label="Razão social", value=ctx.razao_social, width=360)
    cnpj_f = modal_field(label="CNPJ", value=ctx.cnpj, width=360)
    activity_dd = modal_dropdown(
        label="Atividade",
        value=ctx.activity_type,
        width=360,
        options=[ft.dropdown.Option(k, v) for k, v in ACTIVITY_LABELS.items()],
    )
    limit_f = modal_field(label="Limite anual (R$)", value=str(ctx.annual_limit), width=360)
    das_f = modal_field(label="DAS customizado (opcional)", value=str(ctx.custom_das_amount or ""), width=360)

    def save(_):
        # invalid numeric input falls back to defaults
        try:
            annual = float(limit_f.value.replace(",", "."))
        except (TypeError, ValueError):
            annual = 81000.0
        custom = None
        if das_f.value:
            try:
                custom = float(das_f.value.replace(",", "."))
            except (TypeError, ValueError):
                pass
        update_mei_config(
            MeiConfig(
                profile_id=ctx.profile_id,
                razao_social=razao_f.value,
                cnpj=cnpj_f.value,
                activity_type=activity_dd.value or "servico",
                custom_das_amount=custom,
                annual_limit=annual,
            )
        )
        app.close_modal()
        app.show_snack("Perfil MEI atualizado")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [razao_f, cnpj_f, activity_dd, limit_f, das_f,
             ft.ElevatedButton("Salvar", on_click=save, style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE))],
            spacing=12,
            tight=True,
        ),
        title="Editar perfil MEI",
    )


def open_client_modal(app: "OrcFinApp", profile_id: int):
    name_f = modal_field(label="Nome do cliente/tomador", width=360)
    doc_f = modal_field(label="CPF/CNPJ (opcional)", width=360)

    def save(_):
        if not name_f.value:
            return
        create_mei_client(MeiClient(profile_id=profile_id, name=name_f.value, document=doc_f.value))
        app.close_modal()
        app.show_snack("Cliente adicionado")
        app.refresh_current_view()

    app.show_modal(
        ft.Column([name_f, doc_f, ft.ElevatedButton("Salvar", on_click=save)], spacing=12, tight=True),
        title="Novo cliente",
    )


def open_invoice_modal(app: "OrcFinApp", profile_id: int):
    clients = get_mei_clients(profile_id)
    num_f = modal_field(label="Número da NF", width=360)
    tomador_f = modal_field(label="Tomador", width=360)
    value_f = modal_field(label="Valor (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    date_f = modal_field(label="Data emissão (AAAA-MM-DD)", value=date.today().isoformat(), width=360)
    due_f = modal_field(label="Vencimento (AAAA-MM-DD)", value=date.today().isoformat(), width=360)
    client_dd = modal_dropdown(
        label="Cliente cadastrado (opcional)",
        width=360,
        options=[ft.dropdown.Option("", "—")] + [ft.dropdown.Option(str(c.id), c.name) for c in clients],
    )

    def save(_):
        try:
            amount = Decimal(value_f.value.replace(",", "."))
        except Exception:
            app.show_snack("Valor inválido", success=False)
            return
        client_id = int(client_dd.value) if client_dd.value else None
        tomador = tomador_f.value
        if client_id:
            match = next((c for c in clients if c.id == client_id), None)
            if match and not tomador:
                tomador = match.name
        issue = date.fromisoformat(date_f.value)
        due = date.fromisoformat(due_f.value) if due_f.value else issue
        create_mei_invoice(
            MeiInvoice(
                profile_id=profile_id,
                invoice_number=num_f.value or "",
                client_id=client_id,
                tomador_name=tomador,
                amount=amount,
                issue_date=issue,
                due_date=due,
            )
        )
        app.close_modal()
        app.show_snack("NF registrada")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [num_f, tomador_f, value_f, date_f, due_f, client_dd, ft.ElevatedButton("Salvar", on_click=save)],
            spacing=12,
            tight=True,
        ),
        title="Registrar nota fiscal",
    )


def open_quick_sale(app: "OrcFinApp", profile_id: int):
    clients = get_mei_clients(profile_id)
    categories = [c for c in get_categories_for_mode(True) if c.type == TransactionType.INCOME]
    income_cat = categories[0] if categories else None

    if not income_cat:
        app.show_snack("Crie uma categoria de receita MEI", success=False)
        return

    value_f = modal_field(label="Valor (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    desc_f = modal_field(label="Descrição", width=360)
    date_f = modal_field(label="Data", value=date.today().isoformat(), width=360)
    client_dd = modal_dropdown(
        label="Cliente",
        width=360,
        options=[ft.dropdown.Option("", "—")] + [ft.dropdown.Option(str(c.id), c.name) for c in clients],
    )

    def save(_):
        try:
            amount = Decimal(value_f.value.replace(",", "."))
            tx_date = date.fromisoformat(date_f.value)
        except Exception:
            app.show_snack("Dados inválidos", success=False)
            return
        client_id = int(client_dd.value) if client_dd.value else None
        create_transaction(
            Transaction(
                profile_id=profile_id,
                date=tx_date,
                description=desc_f.value or "Receita MEI",
                amount=amount,
                category_id=income_cat.id,
                type=TransactionType.INCOME,
                mei_client_id=client_id,
            )
        )
        app.close_modal()
        app.show_snack("Receita registrada")
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [value_f, desc_f, date_f, client_dd,
             ft.ElevatedButton("Registrar venda", on_click=save, style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE))],
            spacing=12,
            tight=True,
        ),
        title="Nova receita",
    )


def delete_client(app: "OrcFinApp", client_id: int):
    delete_mei_client(client_id)
    app.show_snack("Cliente removido")
    app.refresh_current_view()


def delete_invoice(app: "OrcFinApp", invoice_id: int):
    delete_mei_invoice(invoice_id)
    app.show_snack("NF removida")
    app.refresh_current_view()