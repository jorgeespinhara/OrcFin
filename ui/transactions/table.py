"""Transaction list table."""

from __future__ import annotations

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.transactions import delete_transactions_batch
from core.models import Transaction, TransactionType
from core.domain.value_objects.money import format_brl
from ui.theme import active as theme_colors, on_surface_button_style
from ui.transactions.actions import edit_transaction, open_split_modal, open_transfer_modal
from ui.transactions.detail import show_transaction_detail

def build_batch_delete_button(view) -> ft.OutlinedButton:
    count = len(view._selected_ids)
    view._batch_delete_btn = ft.OutlinedButton(
        f"Excluir selecionados ({count})" if count else "Excluir selecionados",
        icon=ft.Icons.DELETE_OUTLINE,
        disabled=count == 0,
        on_click=lambda e: delete_selected(view, e),
        style=ft.ButtonStyle(
            color="#EF4444" if count else ft.Colors.GREY_500,
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
        ),
    )
    return view._batch_delete_btn

def update_selection_ui(view):
    count = len(view._selected_ids)
    if view._batch_delete_btn:
        view._batch_delete_btn.text = (
            f"Excluir selecionados ({count})" if count else "Excluir selecionados"
        )
        view._batch_delete_btn.disabled = count == 0
        view._batch_delete_btn.style = ft.ButtonStyle(
            color="#EF4444" if count else ft.Colors.GREY_500,
        )
        view._batch_delete_btn.update()
    if view._select_all_check is not None and view.transactions:
        all_ids = {tx.id for tx in view.transactions if tx.id is not None}
        view._select_all_check.value = bool(all_ids) and view._selected_ids >= all_ids
        view._select_all_check.update()

def toggle_select(view, tx_id: int, selected: bool):
    if selected:
        view._selected_ids.add(tx_id)
    else:
        view._selected_ids.discard(tx_id)
    update_selection_ui(view)

def toggle_select_all(view, selected: bool):
    if selected:
        view._selected_ids = {tx.id for tx in view.transactions if tx.id is not None}
    else:
        view._selected_ids.clear()
    update_selection_ui(view)
    view.app.refresh_current_view()

def confirm_delete(view, tx_ids: list[int], summary: str):
    def do_delete(_):
        removed = delete_transactions_batch(tx_ids)
        view._selected_ids -= set(tx_ids)
        view.app.close_modal()
        view.app.show_snack(f"{removed} lançamento(s) excluído(s)")
        view.app.refresh_current_view()

    view.app.show_modal(
        ft.Column(
            [
                ft.Text(summary, color=ft.Colors.WHITE, size=13),
                ft.Text(
                    "Esta ação não pode ser desfeita.",
                    color=ft.Colors.GREY_400,
                    size=11,
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "Cancelar",
                            on_click=lambda _: view.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        ft.ElevatedButton(
                            "Excluir",
                            icon=ft.Icons.DELETE_FOREVER,
                            on_click=do_delete,
                            style=ft.ButtonStyle(bgcolor="#EF4444", color=ft.Colors.WHITE),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title="Confirmar exclusão",
    )

def delete_one(view, tx: Transaction):
    if tx.id is None:
        return
    confirm_delete(view, 
        [tx.id],
        f"Excluir o lançamento \"{tx.description}\" ({format_brl(tx.amount)})?",
    )

def delete_selected(view, _):
    if not view._selected_ids:
        view.app.show_snack("Selecione ao menos um lançamento", success=False)
        return
    ids = list(view._selected_ids)
    confirm_delete(view, 
        ids,
        f"Excluir {len(ids)} lançamento(s) selecionado(s)?",
    )

def build_transactions_table(view) -> ft.Control:
    def on_select_all(ev):
        toggle_select_all(view, ev.control.value)

    view._select_all_check = ft.Checkbox(
        value=False,
        on_change=on_select_all,
    )

    c = theme_colors()
    col_style = ft.TextStyle(color=c.text_primary, weight=ft.FontWeight.W_600)
    columns = [
        ft.DataColumn(ft.Text("", style=col_style)),
        ft.DataColumn(ft.Text("Data", style=col_style)),
        ft.DataColumn(ft.Text("Perfil", style=col_style)),
        ft.DataColumn(ft.Text("Descrição", style=col_style)),
        ft.DataColumn(ft.Text("Categoria", style=col_style)),
        ft.DataColumn(ft.Text("Valor", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("Tipo", style=col_style)),
        ft.DataColumn(ft.Text("", style=col_style)),
    ]
    cell_style = ft.TextStyle(color=c.text_primary, size=12)

    if not view.transactions:
        return ft.Container(
            content=ft.Text(
                "Nenhum lançamento encontrado para o período selecionado.",
                color=theme_colors().text_muted,
                size=14,
            ),
            padding=24,
        )

    rows = []
    for tx in view.transactions:
        profile_name = next((p.name for p in view.profiles if p.id == tx.profile_id), EMPTY_CELL)
        cat = view.category_lookup.get(tx.category_id)
        cat_name = cat.name if cat else EMPTY_CELL
        cat_icon = cat.icon if cat else ""

        value_color = "#22C55E" if tx.type == TransactionType.INCOME else "#EF4444"
        type_badge = ft.Container(
            content=ft.Text(
                "Receita" if tx.type == TransactionType.INCOME else "Despesa",
                size=10,
                color=ft.Colors.WHITE,
            ),
            bgcolor="#22C55E" if tx.type == TransactionType.INCOME else "#EF4444",
            padding=ft.Padding(left=8, top=2, right=8, bottom=2),
            border_radius=6,
        )

        tx_id = tx.id
        is_selected = tx_id in view._selected_ids if tx_id else False

        def on_row_select(ev, tid=tx_id):
            if tid is not None:
                toggle_select(view, tid, ev.control.value)

        desc_cell = ft.Row(
            [
                ft.Text(tx.description, size=12, max_lines=1, expand=True, color=c.text_primary),
                ft.Container(
                    content=ft.Text(
                        f"{tx.installment_number}/{tx.installment_total}",
                        size=9,
                        color=ft.Colors.WHITE,
                    ),
                    bgcolor="#6366F1",
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                    border_radius=6,
                    visible=bool(tx.is_installment and tx.installment_number and tx.installment_total),
                ),
            ],
            spacing=6,
        )

        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Checkbox(value=is_selected, on_change=on_row_select)
                        if tx_id is not None
                        else ft.Container()
                    ),
                    ft.DataCell(ft.Text(tx.date.strftime("%d/%m/%Y"), style=cell_style)),
                    ft.DataCell(ft.Text(profile_name, style=cell_style)),
                    ft.DataCell(desc_cell),
                    ft.DataCell(ft.Text(f"{cat_icon} {cat_name}", style=cell_style)),
                    ft.DataCell(
                        ft.Text(
                            format_brl(tx.amount),
                            size=12,
                            color=value_color,
                            weight=ft.FontWeight.W_600,
                        )
                    ),
                    ft.DataCell(type_badge),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.INFO_OUTLINE,
                                    icon_color=theme_colors().text_muted,
                                    tooltip="Detalhes e origem",
                                    on_click=lambda e, t=tx: show_transaction_detail(view, t),
                                ),
                                ft.IconButton(
                                    ft.Icons.EDIT_OUTLINED,
                                    icon_color="#14B8A6",
                                    tooltip="Editar lançamento",
                                    on_click=lambda e, t=tx: edit_transaction(view, t),
                                ),
                                ft.IconButton(
                                    ft.Icons.CALL_SPLIT,
                                    icon_color="#6366F1",
                                    tooltip="Dividir",
                                    on_click=lambda e, t=tx: open_split_modal(view, t),
                                ),
                                ft.IconButton(
                                    ft.Icons.SWAP_HORIZ,
                                    icon_color="#F59E0B",
                                    tooltip="Transferir",
                                    on_click=lambda e, t=tx: open_transfer_modal(view, t),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color="#EF4444",
                                    tooltip="Excluir lançamento",
                                    on_click=lambda e, t=tx: delete_one(view, t),
                                ),
                            ],
                            spacing=0,
                            tight=True,
                        )
                        if tx_id is not None
                        else ft.Container()
                    ),
                ]
            )
        )

    return ft.Column(
        [
            ft.Row(
                [
                    view._select_all_check,
                    ft.Text("Selecionar todos", size=12, color=theme_colors().text_muted),
                ],
                spacing=4,
            ),
            ft.DataTable(
                columns=columns,
                rows=rows,
                heading_row_color=c.surface_alt,
                data_row_color={"hovered": c.surface_alt},
                border=None,
                column_spacing=16,
                horizontal_lines=ft.border.BorderSide(0.5, c.border),
            ),
        ],
        spacing=8,
    )
