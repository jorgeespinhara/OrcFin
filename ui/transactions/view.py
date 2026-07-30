"""Transaction list and entry form."""
from __future__ import annotations

import asyncio

import flet as ft

from core.db.repositories.categories import get_all_categories, get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from ui.personal.charts import PERSONAL_ACCENT
from ui.personal.period_filter import build_period_filter
from ui.theme import (
    active as theme_colors,
    body_text,
    field_params,
    primary_button_style,
    title_text,
)
from ui.transactions.actions import import_statement, open_new_transaction_modal
from ui.transactions.data import (
    apply_search,
    apply_type_filter,
    clear_search,
    get_type_filter,
    load_transactions,
    period_label_for_view,
)
from ui.transactions.table import (
    build_selection_bar,
    build_summary_strip,
    build_transactions_list,
)


class TransactionsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.profiles = get_all_profiles()
        self.category_lookup = {c.id: c for c in get_all_categories()}
        self.categories = get_categories_for_mode(self.app.is_mei_mode())
        if not hasattr(app, "tx_type_filter"):
            app.tx_type_filter = "all"
        if not hasattr(app, "tx_search_query"):
            app.tx_search_query = ""
        self.transactions = load_transactions(self)
        if not hasattr(app, "tx_selection"):
            app.tx_selection = set()
        self._selected_ids = app.tx_selection
        self._batch_delete_btn: ft.OutlinedButton | None = None
        self._clear_selection_btn: ft.TextButton | None = None
        self._select_all_check: ft.Checkbox | None = None
        self._selection_bar: ft.Container | None = None
        self._selection_label: ft.Text | None = None
        self._search_token = 0

    def build(self) -> ft.Control:
        c = theme_colors()
        context_label = self.app.get_view_context_label()
        current_filter = get_type_filter(self)
        search_value = getattr(self.app, "tx_search_query", "") or ""

        search_field = ft.TextField(
            hint_text="Buscar descrição ou notas",
            prefix_icon=ft.Icons.SEARCH,
            value=search_value,
            expand=True,
            on_submit=lambda e: apply_search(self, e),
            **field_params(accent=PERSONAL_ACCENT),
        )

        def on_search_change(e):
            self._search_token += 1
            token = self._search_token
            raw = e.control.value or ""

            async def _debounce():
                await asyncio.sleep(0.4)
                if token != self._search_token:
                    return
                # Only refresh when query actually changed after debounce.
                if (raw or "").strip() == (getattr(self.app, "tx_search_query", "") or "").strip():
                    return
                apply_search(self, query=raw)

            try:
                self.app.page.run_task(_debounce)
            except Exception:
                apply_search(self, query=raw)

        search_field.on_change = on_search_change

        def filter_btn(value: str, label: str) -> ft.Control:
            selected = current_filter == value
            return ft.Container(
                content=ft.Text(
                    label,
                    size=12,
                    weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                    color=c.text_primary if selected else c.text_secondary,
                ),
                padding=ft.Padding(12, 8, 12, 8),
                bgcolor=c.surface_alt if selected else c.surface,
                border=ft.Border.all(1, c.accent if selected else c.border),
                border_radius=8,
                on_click=lambda _, v=value: apply_type_filter(self, v),
                ink=True,
            )

        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text("Lançamentos"),
                        body_text(f"{context_label} · {period_label_for_view(self)}", size=13),
                    ],
                    spacing=4,
                    tight=True,
                ),
                ft.Container(expand=True),
                build_period_filter(self.app),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        toolbar = ft.Column(
            [
                ft.Row(
                    [
                        search_field,
                        ft.IconButton(
                            ft.Icons.CLEAR,
                            tooltip="Limpar busca",
                            icon_color=c.text_muted,
                            on_click=lambda _: clear_search(self),
                        ),
                        ft.ElevatedButton(
                            "Novo",
                            icon=ft.Icons.ADD,
                            on_click=lambda e: open_new_transaction_modal(self, e),
                            style=primary_button_style(),
                        ),
                        ft.OutlinedButton(
                            "Importar",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=lambda _: import_statement(self),
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        filter_btn("all", "Todos"),
                        filter_btn("income", "Receitas"),
                        filter_btn("expense", "Despesas"),
                    ],
                    spacing=8,
                ),
            ],
            spacing=10,
            tight=True,
        )

        selection_bar = build_selection_bar(self)
        summary = build_summary_strip(self)
        list_body = build_transactions_list(self)

        # Same stable pattern as Dashboard: one scrollable Column, no nested expand hosts.
        controls: list[ft.Control] = [
            header,
            ft.Container(height=12),
            toolbar,
            ft.Container(height=12),
            summary,
        ]
        if selection_bar.visible:
            controls.append(selection_bar)
            controls.append(ft.Container(height=8))
        controls.extend(
            [
                ft.Container(height=4),
                list_body,
                ft.Container(height=16),
            ]
        )

        return ft.Column(
            controls,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )
