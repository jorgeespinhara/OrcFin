"""MEI Vendas — receitas por cliente."""

from __future__ import annotations

import flet as ft

from core.copy import EMPTY_CELL
from core.domain.value_objects.money import format_brl
from core.mei import get_revenue_by_client
from core.i18n import t
from ui.mei.actions import open_quick_sale, open_client_modal, delete_client
from ui.mei.components import mei_text, mei_title, section_card
from ui.mei.constants import MEI_ACCENT
from ui.theme import active as theme_colors, primary_button_style
from ui.mei.context import MeiContext, require_mei_ready
from core.db.repositories.mei import get_mei_clients
from core.db.repositories.transactions import get_transactions
from core.models import TransactionType
from datetime import date


class MeiVendasView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        pid = self.ctx.profile_id
        by_client = get_revenue_by_client(pid)
        clients = get_mei_clients(pid)
        recent = [
            tx for tx in get_transactions(profile_id=pid, limit=30)
            if tx.type == TransactionType.INCOME
        ][:15]

        tc = theme_colors()
        header = ft.Row(
            [
                mei_title(t("mei.sales.title")),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    t("mei.sales.new_revenue"),
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_quick_sale(self.app, pid),
                    style=primary_button_style(bgcolor=MEI_ACCENT),
                ),
                ft.OutlinedButton(
                    t("mei.sales.new_client"),
                    icon=ft.Icons.PERSON_ADD,
                    on_click=lambda _: open_client_modal(self.app, pid),
                ),
            ],
            spacing=8,
        )

        client_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(r["name"], color=tc.text_primary)),
                ft.DataCell(ft.Text(str(r["count"]), color=tc.text_muted)),
                ft.DataCell(ft.Text(format_brl(r["total"]), color=theme_colors().income)),
            ])
            for r in by_client
        ] or [ft.DataRow(cells=[ft.DataCell(mei_text(t("mei.sales.no_revenue_year"), muted=True))] * 3)]

        client_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("mei.sales.col_client"))),
                ft.DataColumn(ft.Text(t("mei.sales.col_entries"))),
                ft.DataColumn(ft.Text(t("mei.sales.col_year_total")), numeric=True),
            ],
            rows=client_rows,
            heading_row_color=tc.surface_alt,
        )

        cadastro_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(client.name, color=tc.text_primary)),
                ft.DataCell(ft.Text(client.document or EMPTY_CELL, color=tc.text_muted)),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=theme_colors().danger,
                                          on_click=lambda e, cid=client.id: delete_client(self.app, cid))),
            ])
            for client in clients
        ] or [ft.DataRow(cells=[ft.DataCell(mei_text(t("mei.sales.no_clients"), muted=True))] * 3)]

        recent_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(tx.date.strftime("%d/%m/%Y"))),
                ft.DataCell(
                    ft.Text(
                        tx.description,
                        color=tc.text_primary,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=tx.description,
                    )
                ),
                ft.DataCell(ft.Text(format_brl(tx.amount), color=theme_colors().income)),
            ])
            for tx in recent
        ]

        return ft.Column(
            [
                header,
                ft.Container(height=16),
                section_card(t("mei.sales.by_client"), client_table),
                ft.Container(height=12),
                section_card(t("mei.sales.registered_clients"), ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(t("mei.sales.col_name"))),
                        ft.DataColumn(ft.Text(t("mei.sales.col_doc"))),
                        ft.DataColumn(ft.Text("")),
                    ],
                    rows=cadastro_rows,
                    heading_row_color=tc.surface_alt,
                )),
                ft.Container(height=12),
                section_card(t("mei.sales.recent"), ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(t("mei.sales.col_date"))),
                        ft.DataColumn(ft.Text(t("mei.sales.col_desc"))),
                        ft.DataColumn(ft.Text(t("mei.sales.col_amount"))),
                    ],
                    rows=recent_rows or [ft.DataRow(cells=[ft.DataCell(ft.Text(EMPTY_CELL))] * 3)],
                    heading_row_color=tc.surface_alt,
                ) if recent_rows else section_card(t("mei.sales.recent"), mei_text(t("mei.sales.no_revenue"), muted=True))),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
