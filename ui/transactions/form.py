"""Create and edit transaction modal."""

from __future__ import annotations

import flet as ft

from datetime import date, datetime
from decimal import Decimal
from core.domain.value_objects.money import format_brl
from core.models import Transaction, TransactionType
from core.db.repositories.transactions import create_transaction, update_transaction, create_internal_transfer, split_transaction
from ui.personal.charts import PERSONAL_ACCENT
from ui.theme import active as theme_colors, segmented_button_style, text_field as themed_field

def show_transaction_form(view, existing_tx: Transaction | None = None):
    is_editing = existing_tx is not None
    initial_date = existing_tx.date if existing_tx else date.today()
    default_profile = (
        existing_tx.profile_id if existing_tx
        else view.app.get_view_profile_id() or (view.profiles[0].id if view.profiles else None)
    )
    initial_type = existing_tx.type if existing_tx else TransactionType.EXPENSE

    selected_profile = ft.Dropdown(
        label="Perfil",
        options=[ft.dropdown.Option(key=str(p.id), text=p.name) for p in view.profiles],
        value=str(default_profile) if default_profile else None,
        expand=True,
    )

    cat_options, cat_default = category_options_for_type(view, initial_type)
    if existing_tx:
        cat_default = str(existing_tx.category_id)
    cat_dropdown = ft.Dropdown(
        label="Categoria",
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
            ft.Segment(value=TransactionType.INCOME.value, label=ft.Text("Receita")),
            ft.Segment(value=TransactionType.EXPENSE.value, label=ft.Text("Despesa")),
        ],
    )

    amount_field = ft.TextField(
        label="Valor (R$)",
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix="R$ ",
        value=str(existing_tx.amount) if existing_tx else None,
        expand=True,
    )

    selected_date = {"value": initial_date}
    date_display = ft.TextField(
        label="Data",
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
        help_text="Selecione dia, mês e ano",
        confirm_text="Confirmar",
        cancel_text="Cancelar",
        barrier_color=theme_colors().modal_scrim,
        on_change=on_date_picked,
    )
    if date_picker not in view.app.page.overlay:
        view.app.page.overlay.append(date_picker)

    def open_calendar(_):
        date_picker.value = selected_date["value"]
        view.app.page.show_dialog(date_picker)

    desc_field = ft.TextField(
        label="Descrição",
        hint_text="Ex: Pagamento salário, Compra supermercado...",
        value=existing_tx.description if existing_tx else None,
        expand=True,
    )

    recurring_check = ft.Checkbox(
        label="Lançamento recorrente",
        value=existing_tx.is_recurring if existing_tx else False,
    )

    installment_check = ft.Checkbox(
        label="Compra parcelada",
        value=False,
        visible=not is_editing,
    )
    installments_field = ft.TextField(
        label="Quantidade de parcelas",
        value="12",
        width=160,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    installment_preview = ft.Text(
        "Informe o valor total e o número de parcelas.",
        size=11,
        color=ft.Colors.GREY_400,
    )

    def refresh_installment_preview(_=None):
        if not installment_check.value:
            installment_preview.value = "Desmarque para lançamento à vista."
            amount_field.label = "Valor (R$)"
            return
        amount_field.label = "Valor total (R$)"
        try:
            total = Decimal((amount_field.value or "0").replace(",", "."))
            parcels = max(int(installments_field.value or "2"), 2)
            per = (total / parcels).quantize(Decimal("0.01"))
            installment_preview.value = (
                f"{parcels}x de {format_brl(per)} (total {format_brl(total)})"
            )
        except Exception:
            installment_preview.value = "Valor ou parcelas inválidos."

    installment_section = ft.Container(
        content=ft.Column(
            [
                ft.Text("Parcelamento manual", size=13, weight=ft.FontWeight.W_600, color="#6366F1"),
                ft.Text(
                    "Ex.: R$ 1.200 em 12x gera 12 lançamentos mensais de R$ 100,00.",
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
        label="Observações (opcional)",
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
            show_form_error("Selecione um perfil.", field=selected_profile)
            return None
        if not cat_dropdown.value:
            show_form_error("Selecione uma categoria.", field=cat_dropdown)
            return None

        description = (desc_field.value or "").strip()
        if not description:
            show_form_error("Informe uma descrição para o lançamento.", field=desc_field)
            return None

        raw_amount = (amount_field.value or "").strip().replace(",", ".")
        if not raw_amount:
            show_form_error("Informe o valor do lançamento.", field=amount_field)
            return None
        try:
            amount = Decimal(raw_amount)
        except Exception:
            show_form_error("Valor inválido. Use apenas números.", field=amount_field)
            return None
        if amount <= 0:
            show_form_error("O valor deve ser maior que zero.", field=amount_field)
            return None

        if selected_date["value"] is None:
            show_form_error("Selecione a data do lançamento.", field=date_display)
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

        profile_id = data["profile_id"]
        category_id = data["category_id"]
        description = data["description"]
        amount = data["amount"]
        tx_date = data["tx_date"]
        tx_type = data["tx_type"]

        if installment_check.value and not is_editing:
            from core.services.import_service import create_installment_plan

            try:
                parcels = int(installments_field.value or "2")
            except ValueError:
                show_form_error("Informe um número válido de parcelas.", field=installments_field)
                return
            if parcels < 2:
                show_form_error("Parcelamento requer pelo menos 2 parcelas.", field=installments_field)
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
            view.app.show_snack(f"{parcels} parcelas criadas!")
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
                    show_form_error("Não foi possível atualizar o lançamento.")
                    return
                success_message = "Lançamento atualizado com sucesso!"
            else:
                create_transaction(tx_payload)
                success_message = "Lançamento registrado com sucesso!"

            view.app.close_modal()
            if budget_msg and not is_editing:
                view.app.show_snack(
                    f"Lançamento salvo. {budget_msg}",
                    success="excedido" not in budget_msg.lower(),
                )
            else:
                view.app.show_snack(success_message)
            view.app.refresh_current_view()

        if budget_msg and "excedido" in budget_msg.lower() and not is_editing:
            view.app.show_modal(
                ft.Column(
                    [
                        ft.Text(budget_msg, color=ft.Colors.AMBER_200, size=13),
                        ft.Row(
                            [
                                ft.TextButton(
                                    "Cancelar",
                                    on_click=lambda _: view.app.close_modal(),
                                    style=on_surface_button_style(),
                                ),
                                ft.ElevatedButton(
                                    "Salvar mesmo assim",
                                    on_click=do_save,
                                    style=ft.ButtonStyle(bgcolor="#EF4444", color=ft.Colors.WHITE),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=12,
                    tight=True,
                ),
                title="Alerta de orçamento",
            )
            return

        do_save()

    def clear_error_on_input(_=None):
        if error_banner.visible:
            error_banner.visible = False
            error_text.value = ""
            view.app.page.update()

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
                            tooltip="Abrir calendário",
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

    form_content = ft.Container(
        content=ft.Column(
            [
                ft.Container(content=form_body, height=400),
                ft.Row(
                    [
                        ft.TextButton("Cancelar", on_click=lambda _: view.app.close_modal()),
                        ft.ElevatedButton(
                            "Salvar alterações" if is_editing else "Salvar Lançamento",
                            on_click=save_transaction,
                            style=ft.ButtonStyle(bgcolor=PERSONAL_ACCENT, color=ft.Colors.WHITE)),
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

    title = "Editar Lançamento" if is_editing else "Novo Lançamento"
    if is_editing and existing_tx.is_installment:
        title = f"Editar parcela {existing_tx.installment_number}/{existing_tx.installment_total}"

    view.app.show_modal(form_content, title=title)

def category_options_for_type(view, tx_type: TransactionType):
    filtered = [c for c in view.categories if c.type == tx_type]
    options = [
        ft.dropdown.Option(key=str(c.id), text=f"{c.icon or ''} {c.name}") for c in filtered
    ]
    default = str(filtered[0].id) if filtered else None
    return options, default

def apply_category_options(view, dropdown: ft.Dropdown, selected_types):
    """Filter categories based on income/expense selection (no control.update)."""
    selected_value = next(iter(selected_types or []), TransactionType.EXPENSE.value)
    tx_type = TransactionType(selected_value)
    options, default = category_options_for_type(view, tx_type)
    dropdown.options = options
    dropdown.value = default
