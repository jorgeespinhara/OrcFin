"""Modals for MEI recurring subscriptions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.mei import get_mei_clients
from core.db.repositories.mei_recurring import (
    create_subscription,
    receive_charge_payment,
    update_subscription_status,
)
from core.i18n import t
from core.models import MeiSubscription
from ui.mei.components import modal_actions, modal_dropdown, modal_field


def open_subscription_modal(app: "OrcFinApp", profile_id: int):
    clients = get_mei_clients(profile_id)
    name_f = modal_field(label=t("mei.recurring.contract_name"), width=360)
    amount_f = modal_field(label=t("mei.recurring.monthly_amount"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
    due_f = modal_field(label=t("mei.recurring.due_day"), value="10", width=360, keyboard_type=ft.KeyboardType.NUMBER)
    start_f = modal_field(label=t("mei.recurring.start"), value=date.today().isoformat(), width=360)
    notes_f = modal_field(label=t("mei.recurring.notes"), width=360)
    client_dd = modal_dropdown(
        label=t("mei.recurring.client"),
        width=360,
        options=[ft.dropdown.Option("", EMPTY_CELL)] + [ft.dropdown.Option(str(c.id), c.name) for c in clients],
    )

    def save(_):
        if not name_f.value:
            app.show_snack(t("mei.recurring.need_name"), success=False)
            return
        try:
            amount = Decimal(amount_f.value.replace(",", "."))
            due_day = int(due_f.value)
            start = date.fromisoformat(start_f.value)
            if due_day < 1 or due_day > 28:
                raise ValueError("due_day")
        except Exception:
            app.show_snack(t("mei.recurring.invalid"), success=False)
            return
        client_id = int(client_dd.value) if client_dd.value else None
        create_subscription(
            MeiSubscription(
                profile_id=profile_id,
                client_id=client_id,
                name=name_f.value,
                monthly_amount=amount,
                due_day=due_day,
                start_date=start,
                notes=notes_f.value,
            )
        )
        app.close_modal()
        app.show_snack(t("mei.recurring.created"))
        app.refresh_current_view()

    app.show_modal(
        ft.Column(
            [name_f, amount_f, due_f, start_f, client_dd, notes_f, modal_actions(app, t("common.save"), save)],
            spacing=12,
            tight=True,
        ),
        title=t("mei.recurring.new_title"),
    )


def confirm_receive_charge(app: "OrcFinApp", profile_id: int, charge_id: int):
    tx_id = receive_charge_payment(profile_id, charge_id)
    app.show_snack(
        t("mei.recurring.receive_ok") if tx_id else t("mei.recurring.receive_fail"),
        success=bool(tx_id),
    )
    app.refresh_current_view()


def confirm_pause_subscription(app: "OrcFinApp", subscription_id: int):
    if update_subscription_status(subscription_id, "paused"):
        app.show_snack(t("mei.recurring.paused"))
        app.refresh_current_view()


def confirm_cancel_subscription(app: "OrcFinApp", subscription_id: int):
    if update_subscription_status(subscription_id, "cancelled"):
        app.show_snack(t("mei.recurring.ended"))
        app.refresh_current_view()
