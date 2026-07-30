"""Transaction list - grouped rows with compact actions."""

from __future__ import annotations

from decimal import Decimal

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.transactions import delete_transactions_batch
from core.domain.value_objects.money import format_brl
from core.models import Transaction, TransactionType
from ui.theme import (
    active as theme_colors,
    danger_button_style,
    empty_state,
    on_surface_button_style,
)
from ui.transactions.actions import (
    edit_transaction,
    open_new_transaction_modal,
    open_split_modal,
    open_transfer_modal,
)
from ui.transactions.data import (
    TX_LIST_LIMIT,
    format_date_header,
    get_type_filter,
    group_by_date,
    list_totals,
)
from ui.transactions.detail import show_transaction_detail

# Back-compat alias
build_transactions_table = None  # set below


def build_batch_delete_button(view) -> ft.OutlinedButton:
    c = theme_colors()
    count = len(view._selected_ids)
    view._batch_delete_btn = ft.OutlinedButton(
        f"Excluir ({count})" if count else "Excluir",
        icon=ft.Icons.DELETE_OUTLINE,
        disabled=count == 0,
        on_click=lambda e: delete_selected(view, e),
        style=ft.ButtonStyle(
            color=c.danger if count else c.text_muted,
            padding=ft.Padding(left=16, top=10, right=16, bottom=10),
        ),
    )
    return view._batch_delete_btn


def build_clear_selection_button(view) -> ft.TextButton:
    view._clear_selection_btn = ft.TextButton(
        "Limpar seleção",
        on_click=lambda _: clear_selection(view),
        style=on_surface_button_style(),
    )
    return view._clear_selection_btn


def update_selection_ui(view):
    c = theme_colors()
    count = len(view._selected_ids)
    if getattr(view, "_batch_delete_btn", None):
        view._batch_delete_btn.text = f"Excluir ({count})" if count else "Excluir"
        view._batch_delete_btn.disabled = count == 0
        view._batch_delete_btn.style = ft.ButtonStyle(color=c.danger if count else c.text_muted)
        try:
            view._batch_delete_btn.update()
        except Exception:
            pass
    if getattr(view, "_selection_bar", None):
        view._selection_bar.visible = count > 0
        if getattr(view, "_selection_label", None):
            view._selection_label.value = f"{count} selecionado(s)"
            try:
                view._selection_label.update()
            except Exception:
                pass
        try:
            view._selection_bar.update()
        except Exception:
            pass
    if view._select_all_check is not None and view.transactions:
        all_ids = {tx.id for tx in view.transactions if tx.id is not None}
        view._select_all_check.value = bool(all_ids) and view._selected_ids >= all_ids
        try:
            view._select_all_check.update()
        except Exception:
            pass


def toggle_select(view, tx_id: int, selected: bool):
    if selected:
        view._selected_ids.add(tx_id)
    else:
        view._selected_ids.discard(tx_id)
    update_selection_ui(view)


def clear_selection(view):
    view._selected_ids.clear()
    view.app.refresh_current_view()


def toggle_select_all(view, selected: bool):
    if selected:
        view._selected_ids = {tx.id for tx in view.transactions if tx.id is not None}
    else:
        view._selected_ids.clear()
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
                ft.Text(summary, color=theme_colors().text_primary, size=13),
                ft.Text(
                    "Esta ação não pode ser desfeita.",
                    color=theme_colors().text_muted,
                    size=12,
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
                            style=danger_button_style(),
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
    confirm_delete(
        view,
        [tx.id],
        f'Excluir o lançamento "{tx.description}" ({format_brl(tx.amount)})?',
    )


def delete_selected(view, _):
    if not view._selected_ids:
        view.app.show_snack("Selecione ao menos um lançamento", success=False)
        return
    ids = list(view._selected_ids)
    confirm_delete(view, ids, f"Excluir {len(ids)} lançamento(s) selecionado(s)?")


def _amount_text(tx: Transaction, c) -> ft.Text:
    is_income = tx.type == TransactionType.INCOME
    sign = "+" if is_income else "-"
    color = c.income if is_income else c.danger
    label = f"{sign} {format_brl(tx.amount)}"
    return ft.Text(
        label,
        size=13,
        color=color,
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.RIGHT,
        tooltip=f"{'Receita' if is_income else 'Despesa'} · {format_brl(tx.amount)}",
    )


def _open_row_actions(view, tx: Transaction):
    """Modal menu - more reliable than PopupMenuButton in dense lists."""
    c = theme_colors()

    def close_and(fn):
        def handler(_):
            view.app.close_modal()
            fn()

        return handler

    view.app.show_modal(
        ft.Column(
            [
                ft.Text(tx.description, size=13, color=c.text_primary, weight=ft.FontWeight.W_600),
                ft.TextButton(
                    "Detalhes e origem",
                    icon=ft.Icons.INFO_OUTLINE,
                    on_click=close_and(lambda: show_transaction_detail(view, tx)),
                    style=on_surface_button_style(),
                ),
                ft.TextButton(
                    "Editar",
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=close_and(lambda: edit_transaction(view, tx)),
                    style=on_surface_button_style(),
                ),
                ft.TextButton(
                    "Dividir",
                    icon=ft.Icons.CALL_SPLIT,
                    on_click=close_and(lambda: open_split_modal(view, tx)),
                    style=on_surface_button_style(),
                ),
                ft.TextButton(
                    "Transferir",
                    icon=ft.Icons.SWAP_HORIZ,
                    on_click=close_and(lambda: open_transfer_modal(view, tx)),
                    style=on_surface_button_style(),
                ),
                ft.TextButton(
                    "Excluir",
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=close_and(lambda: delete_one(view, tx)),
                    style=ft.ButtonStyle(color=c.danger),
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "Fechar",
                            on_click=lambda _: view.app.close_modal(),
                            style=on_surface_button_style(),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=4,
            tight=True,
        ),
        title="Ações do lançamento",
    )


def _tx_row(view, tx: Transaction, *, show_profile: bool) -> ft.Control:
    c = theme_colors()
    tx_id = tx.id
    is_selected = tx_id in view._selected_ids if tx_id else False
    cat = view.category_lookup.get(tx.category_id)
    cat_name = cat.name if cat else EMPTY_CELL
    cat_icon = (cat.icon or "") if cat else ""
    profile_name = next((p.name for p in view.profiles if p.id == tx.profile_id), EMPTY_CELL)

    def on_row_select(ev, tid=tx_id):
        if tid is not None:
            toggle_select(view, tid, ev.control.value)

    meta_bits = [f"{cat_icon} {cat_name}".strip()]
    if show_profile:
        meta_bits.insert(0, profile_name)
    if tx.is_installment and tx.installment_number and tx.installment_total:
        meta_bits.append(f"parcela {tx.installment_number}/{tx.installment_total}")

    return ft.Container(
        content=ft.Row(
            [
                ft.Checkbox(
                    value=is_selected,
                    on_change=on_row_select,
                )
                if tx_id is not None
                else ft.Container(width=40),
                ft.Column(
                    [
                        ft.Text(
                            tx.description,
                            size=13,
                            weight=ft.FontWeight.W_500,
                            color=c.text_primary,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=tx.description,
                        ),
                        ft.Text(
                            " · ".join(meta_bits),
                            size=11,
                            color=c.text_muted,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=" · ".join(meta_bits),
                        ),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                ft.Container(content=_amount_text(tx, c), width=120),
                ft.IconButton(
                    ft.Icons.MORE_VERT,
                    icon_color=c.text_muted,
                    tooltip="Ações",
                    on_click=lambda _, t=tx: _open_row_actions(view, t),
                )
                if tx_id is not None
                else ft.Container(width=40),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(8, 10, 4, 10),
        border=ft.Border.only(bottom=ft.BorderSide(1, c.border)),
        bgcolor=c.surface_alt if is_selected else c.surface,
    )


def build_selection_bar(view) -> ft.Container:
    c = theme_colors()
    count = len(view._selected_ids)
    view._selection_label = ft.Text(
        f"{count} selecionado(s)",
        size=13,
        weight=ft.FontWeight.W_600,
        color=c.text_primary,
    )
    view._selection_bar = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=c.accent, size=20),
                view._selection_label,
                ft.Container(expand=True),
                build_clear_selection_button(view),
                build_batch_delete_button(view),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 10, 12, 10),
        bgcolor=c.surface_alt,
        border=ft.Border.all(1, c.accent),
        border_radius=10,
        visible=count > 0,
    )
    return view._selection_bar


def build_summary_strip(view) -> ft.Control:
    c = theme_colors()
    totals = list_totals(view.transactions)
    query = getattr(view.app, "tx_search_query", "").strip()
    type_filter = get_type_filter(view)

    def metric(label: str, value: str, color: str | None = None) -> ft.Column:
        return ft.Column(
            [
                ft.Text(label, size=11, color=c.text_muted),
                ft.Text(
                    value,
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=color or c.text_primary,
                    tooltip=value,
                ),
            ],
            spacing=2,
            tight=True,
        )

    chips: list[ft.Control] = [
        metric("Receitas", format_brl(totals["income"]), c.income),
        metric("Despesas", format_brl(totals["expense"]), c.danger),
        metric("Saldo", format_brl(totals["net"]), c.success if totals["net"] >= 0 else c.danger),
        metric("Lançamentos", str(totals["count"])),
    ]

    hints: list[ft.Control] = []
    if query:
        hints.append(
            ft.Text(
                f'Busca: "{query}" · {totals["count"]} resultado(s)',
                size=12,
                color=c.text_secondary,
            )
        )
    if type_filter != "all":
        label = "receitas" if type_filter == "income" else "despesas"
        hints.append(ft.Text(f"Filtro: só {label}", size=12, color=c.text_secondary))
    if totals["capped"]:
        hints.append(
            ft.Text(
                f"Mostrando até {TX_LIST_LIMIT} mais recentes - refine o período ou a busca.",
                size=12,
                color=c.warning,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(chips, spacing=28, wrap=True),
                *hints,
            ],
            spacing=8,
            tight=True,
        ),
        padding=ft.Padding(14, 12, 14, 12),
        bgcolor=c.surface,
        border=ft.Border.all(1, c.border),
        border_radius=12,
    )


def build_transactions_list(view) -> ft.Control:
    """Flat list body for the page scroll (no nested expand/scroll)."""
    c = theme_colors()
    show_profile = bool(view.app.is_consolidated)
    query = getattr(view.app, "tx_search_query", "").strip()

    def on_select_all(ev):
        toggle_select_all(view, ev.control.value)

    view._select_all_check = ft.Checkbox(value=False, on_change=on_select_all)
    if view.transactions:
        all_ids = {tx.id for tx in view.transactions if tx.id is not None}
        view._select_all_check.value = bool(all_ids) and view._selected_ids >= all_ids

    if not view.transactions:
        if query:
            body = empty_state(
                icon=ft.Icons.SEARCH_OFF,
                title=f'Nada para "{query}"',
                message="Tente outro termo, limpe a busca ou mude o período/filtro de tipo.",
                action_label="Limpar busca",
                on_action=lambda _: __import__(
                    "ui.transactions.data", fromlist=["clear_search"]
                ).clear_search(view),
            )
        else:
            type_filter = get_type_filter(view)
            if type_filter != "all":
                body = empty_state(
                    icon=ft.Icons.FILTER_ALT_OFF,
                    title="Nenhum lançamento com este filtro",
                    message="Não há receitas ou despesas neste período com o tipo selecionado.",
                    action_label="Ver todos",
                    on_action=lambda _: __import__(
                        "ui.transactions.data", fromlist=["apply_type_filter"]
                    ).apply_type_filter(view, "all"),
                )
            else:
                body = empty_state(
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    title="Nenhum lançamento neste período",
                    message="Cadastre um lançamento ou importe extrato/fatura para começar.",
                    action_label="Novo lançamento",
                    on_action=lambda e: open_new_transaction_modal(view, e),
                )
        body.expand = False
        return ft.Container(
            content=body,
            bgcolor=c.surface,
            border=ft.Border.all(1, c.border),
            border_radius=12,
            padding=8,
        )

    groups = group_by_date(view.transactions)
    sections: list[ft.Control] = [
        ft.Container(
            content=ft.Row(
                [
                    view._select_all_check,
                    ft.Text("Selecionar todos os visíveis", size=12, color=c.text_muted),
                ],
                spacing=6,
            ),
            padding=ft.Padding(8, 8, 8, 4),
        ),
    ]

    for day, day_txs in groups:
        header = format_date_header(day)
        inc = sum(
            (Decimal(str(t.amount)) for t in day_txs if t.type == TransactionType.INCOME),
            Decimal("0"),
        )
        exp = sum(
            (Decimal(str(t.amount)) for t in day_txs if t.type == TransactionType.EXPENSE),
            Decimal("0"),
        )
        day_net = inc - exp
        day_hint = f"{len(day_txs)} · saldo do dia {format_brl(day_net)}"

        sections.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(header, size=13, weight=ft.FontWeight.W_600, color=c.text_primary),
                        ft.Container(expand=True),
                        ft.Text(day_hint, size=11, color=c.text_muted),
                    ],
                ),
                padding=ft.Padding(8, 12, 8, 6),
                bgcolor=c.surface_alt,
            )
        )
        for tx in day_txs:
            sections.append(_tx_row(view, tx, show_profile=show_profile))

    return ft.Container(
        content=ft.Column(sections, spacing=0, tight=True),
        bgcolor=c.surface,
        border=ft.Border.all(1, c.border),
        border_radius=12,
        padding=ft.Padding(0, 0, 0, 8),
    )


def build_transactions_table(view) -> ft.Control:
    """Alias kept for older imports."""
    return build_transactions_list(view)
