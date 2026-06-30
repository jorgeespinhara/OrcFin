"""Transaction list and entry form."""
from __future__ import annotations

import flet as ft
from datetime import date, datetime
from decimal import Decimal
from calendar import monthrange

from core.db.repositories.categories import get_all_categories, get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import (
    create_internal_transfer,
    create_transaction,
    delete_transactions_batch,
    get_transactions,
    search_transactions,
    split_transaction,
    update_transaction,
)
from core.models import Transaction, TransactionType
from core.domain.value_objects.money import format_brl
from ui.theme import (
    active as theme_colors,
    text_field as themed_field,
    title_text,
    body_text,
    field_params,
    on_surface_button_style,
)
from ui.personal.charts import PERSONAL_ACCENT
from ui.personal.period_filter import MONTH_OPTIONS, period_label, build_period_filter

from ui.transactions.data import load_transactions, period_label_for_view, apply_search, clear_search
from ui.transactions.table import build_batch_delete_button, build_transactions_table
from ui.transactions.actions import open_new_transaction_modal, import_statement

class TransactionsView:
    def __init__(self, app: "OrcFinApp"):
            self.app = app
            self.profiles = get_all_profiles()
            self.category_lookup = {c.id: c for c in get_all_categories()}
            self.categories = get_categories_for_mode(self.app.is_mei_mode())
            self.transactions = self.transactions = load_transactions(self)
            if not hasattr(app, "tx_selection"):
                app.tx_selection = set()
            self._selected_ids = app.tx_selection
            self._batch_delete_btn: ft.OutlinedButton | None = None
            self._select_all_check: ft.Checkbox | None = None

    def build(self) -> ft.Control:
        context_label = self.app.get_view_context_label()
        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text("Lançamentos"),
                        body_text(f"{context_label} • {period_label_for_view(self)}", size=13),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                build_period_filter(self.app),
                ft.ElevatedButton(
                    "Novo Lançamento",
                    icon=ft.Icons.ADD,
                    on_click=lambda e: open_new_transaction_modal(self, e),
                    style=ft.ButtonStyle(
                        bgcolor="#14B8A6",
                        color=ft.Colors.WHITE,
                        padding=ft.Padding(left=24, top=12, right=24, bottom=12),
                    ),
                ),
                ft.OutlinedButton(
                    "Importar Fatura",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=lambda _: import_statement(self),
                    style=ft.ButtonStyle(
                        padding=ft.Padding(left=20, top=12, right=20, bottom=12),
                    ),
                ),
                build_batch_delete_button(self),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        search_row = ft.Row(
            [
                ft.TextField(
                    hint_text="Buscar descrição ou notas (Enter)",
                    prefix_icon=ft.Icons.SEARCH,
                    value=getattr(self.app, "tx_search_query", ""),
                    expand=True,
                    on_submit=lambda e: apply_search(self, e),
                    **field_params(accent=PERSONAL_ACCENT),
                ),
                ft.IconButton(
                    ft.Icons.CLEAR,
                    tooltip="Limpar busca",
                    icon_color=ft.Colors.GREY_400,
                    on_click=lambda _: clear_search(self),
                ),
            ],
            spacing=8,
        )

        table = build_transactions_table(self)

        return ft.Column(
            [
                header,
                ft.Container(height=8),
                search_row,
                ft.Container(height=12),
                ft.Container(
                    content=table,
                    expand=True,
                    border=ft.border.BorderSide(1, theme_colors().border),
                    border_radius=12,
                    bgcolor=theme_colors().surface,
                ),
            ],
            expand=True,
        )