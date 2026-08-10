"""Create and edit transaction modal."""

from __future__ import annotations

import flet as ft

from datetime import date, datetime
from decimal import Decimal
from core.domain.value_objects.money import format_brl
from core.db.repositories.categories import display_name
from core.i18n import t
from core.models import Transaction, TransactionType
from core.db.repositories.transactions import create_transaction, update_transaction, create_internal_transfer, split_transaction
from ui.personal.charts import PERSONAL_ACCENT
from ui.theme import (
    active as theme_colors,
    danger_button_style,
    on_surface_button_style,
    primary_button_style,
    segmented_button_style,
    text_field as themed_field,
)
from ui.transactions.data import format_amount_input, parse_brl_amount, recent_category_ids

def show_transaction_form(view, existing_tx: Transaction | None = None):
    is_editing = existing_tx is not None
    initial_date = existing_tx.date if existing_tx else date.today()
    default_profile = (
        existing_tx.profile_id if existing_tx
        else view.app.get_view_profile_id() or (view.profiles[0].id if view.profiles else None)
    )
    initial_type = existing_tx.type if existing_tx else TransactionType.EXPENSE

    selected_profile = ft.Dropdown(
        label=t("tx.form.profile"),
        options=[ft.dropdown.Option(key=str(p.id), text=p.name) for p in view.profiles],
        value=str(default_profile) if default_profile else None,
        expand=True,
    )

    cat_options, cat_default = category_options_for_type(
        view,
        initial_type,
        preferred_id=existing_tx.category_id if existing_tx else None,
    )
    cat_dropdown = ft.Dropdown(
        label=t("tx.form.category"),
        options=cat_options,
        value=cat_default,
        expand=True,
    )

    def on_type_change(ev):
        apply_category_options(view, cat_dropdown, ev.control.selected)
        view.app.page.update()

    selected_type = ft.SegmentedButton(
        selected=[initial_type.value],
        on_change=on_type_change,
        style=segmented_button_style(accent=PERSONAL_ACCENT),
        segments=[
            ft.Segment(value=TransactionType.INCOME.value, label=ft.Text(t("tx.income"))),
            ft.Segment(value=TransactionType.EXPENSE.value, label=ft.Text(t("tx.expense"))),
        ],
    )

    amount_field = ft.TextField(
        label=t("tx.form.amount"),
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix="R$ ",
        value=format_amount_input(existing_tx.amount) if existing_tx else None,
        expand=True,
        hint_text=t("tx.form.amount_hint"),
    )

    selected_date = {"value": initial_date}
    date_display = ft.TextField(
        label=t("tx.form.date"),
        value=initial_date.strftime("%d/%m/%Y"),
        read_only=True,
        expand=True,
    )

    def on_date_picked(_):
        picked = date_picker.value
        if picked is None:
            return
        if isinstance(picked, datetime):
            picked = picked.date()
        selected_date["value"] = picked
        date_display.value = picked.strftime("%d/%m/%Y")
        date_display.error_text = None
        error_banner.visible = False
        view.app.page.update()

    date_picker = ft.DatePicker(
        value=initial_date,
        first_date=date(2000, 1, 1),
        last_date=date(2100, 12, 31),
        entry_mode=ft.DatePickerEntryMode.CALENDAR,
        help_text=t("tx.form.date_help"),
        confirm_text=t("common.confirm"),
        cancel_text=t("common.cancel"),
        barrier_color=theme_colors().modal_scrim,
        on_change=on_date_picked,
    )
    if date_picker not in view.app.page.overlay:
        view.app.page.overlay.append(date_picker)

    def open_calendar(_):
        date_picker.value = selected_date["value"]
        view.app.page.show_dialog(date_picker)

    desc_field = ft.TextField(
        label=t("tx.form.description"),
        hint_text=t("tx.form.description_hint"),
        value=existing_tx.description if existing_tx else None,
        expand=True,
    )

    recurring_check = ft.Checkbox(
        label=t("tx.form.recurring"),
        value=existing_tx.is_recurring if existing_tx else False,
    )

    installment_check = ft.Checkbox(
        label=t("tx.form.installment_check"),
        value=False,
        visible=not is_editing,
    )
    installments_field = ft.TextField(
        label=t("tx.form.installment_count"),
        value="12",
        width=160,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    installment_preview = ft.Text(
        t("tx.form.installment_preview_hint"),
        size=11,
        color=theme_colors().text_muted,
    )

    def refresh_installment_preview(_=None):
        if not installment_check.value:
            installment_preview.value = t("tx.form.installment_cash")
            amount_field.label = t("tx.form.amount")
            return
        amount_field.label = t("tx.form.amount_total")
        try:
            total = parse_brl_amount(amount_field.value or "0")
            parcels = max(int(installments_field.value or "2"), 2)
            per = (total / parcels).quantize(Decimal("0.01"))
            installment_preview.value = t(
                "tx.form.installment_preview",
                count=parcels,
                per=format_brl(per),
                total=format_brl(total),
            )
        except Exception:
            installment_preview.value = t("tx.form.installment_invalid")

    installment_section = ft.Container(
        content=ft.Column(
            [
                ft.Text(t("tx.installments"), size=13, weight=ft.FontWeight.W_600, color=theme_colors().accent_portfolio),
                ft.Text(
                    t("tx.form.installment_example"),
                    size=11,
                    color=theme_colors().text_muted,
                ),
                ft.Row([installments_field], spacing=12),
                installment_preview,
            ],
            spacing=8,
        ),
        bgcolor=theme_colors().installment_bg,
        border=ft.Border.all(1, theme_colors().border),
        border_radius=10,
        padding=12,
        visible=False,
    )

    def on_installment_toggle(ev):
        installment_section.visible = ev.control.value
        refresh_installment_preview()
        view.app.page.update()

    def on_installment_fields_change(_):
        refresh_installment_preview()
        view.app.page.update()

    installment_check.on_change = on_installment_toggle
    amount_field.on_change = on_installment_fields_change
    installments_field.on_change = on_installment_fields_change

    notes_field = themed_field(
        accent=PERSONAL_ACCENT,
        label=t("tx.form.notes"),
        multiline=True,
        min_lines=2,
        max_lines=2,
        value=existing_tx.notes if existing_tx and existing_tx.notes else None,
        expand=True,
    )

    error_text = ft.Text("", size=13, color=theme_colors().error_text, expand=True)
    error_banner = ft.Container(
        visible=False,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=theme_colors().error_text, size=20),
                error_text,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=theme_colors().error_banner_bg,
        border=ft.Border.all(1, theme_colors().error_banner_border),
        border_radius=8,
        padding=12,
    )

    def clear_field_errors():
        for field in (selected_profile, cat_dropdown, amount_field, date_display, desc_field):
            field.error_text = None

    def show_form_error(message: str, *, field: ft.Control | None = None):
        clear_field_errors()
        error_text.value = message
        error_banner.visible = True
        if field is not None:
            field.error_text = message
        view.app.page.update()

    def validate_form() -> dict | None:
        clear_field_errors()
        error_banner.visible = False

        if not selected_profile.value:
            show_form_error(t("tx.form.err_profile"), field=selected_profile)
            return None
        if not cat_dropdown.value:
            show_form_error(t("tx.form.err_category"), field=cat_dropdown)
            return None

        description = (desc_field.value or "").strip()
        if not description:
            show_form_error(t("tx.form.err_description"), field=desc_field)
            return None

        raw_amount = (amount_field.value or "").strip()
        if not raw_amount:
            show_form_error(t("tx.form.err_amount"), field=amount_field)
            return None
        try:
            amount = parse_brl_amount(raw_amount)
        except Exception:
            show_form_error(t("tx.form.err_amount_format"), field=amount_field)
            return None
        if amount <= 0:
            show_form_error(t("tx.form.err_amount_positive"), field=amount_field)
            return None

        if selected_date["value"] is None:
            show_form_error(t("tx.form.err_date"), field=date_display)
            return None

        tx_type = TransactionType(next(iter(selected_type.selected), TransactionType.EXPENSE.value))
        return {
            "profile_id": int(selected_profile.value),
            "category_id": int(cat_dropdown.value),
            "description": description,
            "amount": amount,
            "tx_date": selected_date["value"],
            "tx_type": tx_type,
        }

    def save_transaction(ev):
        data = validate_form()
        if not data:
            return

        save_btn.disabled = True
        view.app.page.update()

        profile_id = data["profile_id"]
        category_id = data["category_id"]
        description = data["description"]
        amount = data["amount"]
        tx_date = data["tx_date"]
        tx_type = data["tx_type"]

        try:
            if installment_check.value and not is_editing:
                from core.services.import_service import create_installment_plan

                try:
                    parcels = int(installments_field.value or "2")
                except ValueError:
                    show_form_error(t("tx.form.err_installments"), field=installments_field)
                    return
                if parcels < 2:
                    show_form_error(t("tx.form.err_installments_min"), field=installments_field)
                    return
                create_installment_plan(
                    profile_id=profile_id,
                    category_id=category_id,
                    description=description,
                    total_amount=amount,
                    installments=parcels,
                    start_date=tx_date,
                    tx_type=tx_type,
                )
                view.app.close_modal()
                view.app.show_snack(t("tx.form.installments_created", count=parcels))
                view.app.refresh_current_view()
                return

            tx_payload = Transaction(
                id=existing_tx.id if existing_tx else None,
                profile_id=profile_id,
                date=tx_date,
                description=description,
                amount=amount,
                category_id=category_id,
                type=tx_type,
                is_recurring=recurring_check.value,
                notes=notes_field.value.strip() or None,
                is_installment=existing_tx.is_installment if existing_tx else False,
                installment_group_id=existing_tx.installment_group_id if existing_tx else None,
                installment_number=existing_tx.installment_number if existing_tx else None,
                installment_total=existing_tx.installment_total if existing_tx else None,
                mei_client_id=existing_tx.mei_client_id if existing_tx else None,
            )

            from core.engine.budget_alerts import check_budget_impact

            budget_msg = check_budget_impact(
                profile_id, category_id, amount, tx_date, tx_type
            )

            def do_save(_=None):
                if is_editing:
                    if not update_transaction(tx_payload):
                        show_form_error(t("tx.form.err_update"))
                        return
                    success_message = t("tx.form.updated")
                else:
                    create_transaction(tx_payload)
                    success_message = t("tx.form.created")

                view.app.close_modal()
                if budget_msg and not is_editing:
                    view.app.show_snack(
                        t("tx.form.saved_budget", budget_msg=budget_msg),
                        success="excedido" not in budget_msg.lower(),
                    )
                else:
                    view.app.show_snack(success_message)
                view.app.refresh_current_view()

            if budget_msg and "excedido" in budget_msg.lower() and not is_editing:
                save_btn.disabled = False
                view.app.show_modal(
                    ft.Column(
                        [
                            ft.Text(budget_msg, color=theme_colors().warning, size=13),
                            ft.Row(
                                [
                                    ft.TextButton(
                                        t("common.cancel"),
                                        on_click=lambda _: view.app.close_modal(),
                                        style=on_surface_button_style(),
                                    ),
                                    ft.ElevatedButton(
                                        t("tx.form.save_anyway"),
                                        on_click=do_save,
                                        style=danger_button_style(),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    title=t("tx.form.budget_alert"),
                )
                return

            do_save()
        finally:
            if save_btn.page is not None:
                save_btn.disabled = False
                try:
                    view.app.page.update()
                except Exception:
                    pass

    def clear_error_on_input(_=None):
        if error_banner.visible:
            error_banner.visible = False
            error_text.value = ""
            view.app.page.update()

    def on_amount_blur(_=None):
        try:
            parsed = parse_brl_amount(amount_field.value)
            amount_field.value = format_amount_input(parsed)
            amount_field.error_text = None
        except Exception:
            pass
        clear_error_on_input()
        view.app.page.update()

    amount_field.on_blur = on_amount_blur

    for field in (desc_field, amount_field, selected_profile, cat_dropdown):
        field.on_change = clear_error_on_input

    form_body = ft.Column(
        [
            error_banner,
            ft.Row([selected_profile], spacing=12),
            ft.Row([selected_type], spacing=12),
            ft.Row([cat_dropdown, amount_field], spacing=12),
            ft.Row(
                [
                    ft.Row(
                        [date_display, ft.IconButton(
                            icon=ft.Icons.CALENDAR_MONTH,
                            tooltip=t("tx.form.open_calendar"),
                            icon_color=PERSONAL_ACCENT,
                            on_click=open_calendar,
                        )],
                        expand=True,
                        spacing=4,
                    ),
                    desc_field,
                ],
                spacing=12,
            ),
            ft.Row([recurring_check, installment_check], spacing=12),
            installment_section,
            notes_field,
        ],
        spacing=12,
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )

    save_btn = ft.ElevatedButton(
        t("tx.form.save_edit") if is_editing else t("tx.form.save_new"),
        on_click=save_transaction,
        style=primary_button_style(bgcolor=PERSONAL_ACCENT),
    )

    form_content = ft.Container(
        content=ft.Column(
            [
                ft.Container(content=form_body, height=400),
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"),
                            on_click=lambda _: view.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        save_btn,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        width=600,
        padding=ft.Padding(4, 0, 4, 0),
    )

    title = t("tx.form.edit_title") if is_editing else t("tx.form.new_title")
    if is_editing and existing_tx.is_installment:
        title = t(
            "tx.form.edit_installment",
            number=existing_tx.installment_number,
            total=existing_tx.installment_total,
        )

    view.app.show_modal(form_content, title=title)


def category_options_for_type(
    view,
    tx_type: TransactionType,
    preferred_id: int | None = None,
):
    filtered = [c for c in view.categories if c.type == tx_type]
    rec_ids = recent_category_ids(view, tx_type)
    recent = set(rec_ids)
    ordered = sorted(
        filtered,
        key=lambda c: (0 if c.id in recent else 1, display_name(c).lower()),
    )
    options = [
        ft.dropdown.Option(
            key=str(c.id),
            text=f"{'★ ' if c.id in recent else ''}{c.icon or ''} {display_name(c)}".strip(),
        )
        for c in ordered
    ]
    if preferred_id and any(c.id == preferred_id for c in ordered):
        default = str(preferred_id)
    elif rec_ids:
        default = str(rec_ids[0])
    else:
        default = str(ordered[0].id) if ordered else None
    return options, default


def apply_category_options(view, dropdown: ft.Dropdown, selected_types):
    """Filter categories based on income/expense selection (no control.update)."""
    selected_value = next(iter(selected_types or []), TransactionType.EXPENSE.value)
    tx_type = TransactionType(selected_value)
    options, default = category_options_for_type(view, tx_type)
    dropdown.options = options
    dropdown.value = default
