"""MEI Vendas — receitas por cliente."""

from __future__ import annotations

import flet as ft

from core.domain.value_objects.money import format_brl
from core.mei import get_revenue_by_client
from ui.mei.actions import open_quick_sale, open_client_modal, delete_client
from ui.mei.components import section_card
from ui.mei.constants import MEI_ACCENT
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
            t for t in get_transactions(profile_id=pid, limit=30)
            if t.type == TransactionType.INCOME
        ][:15]

        header = ft.Row(
            [
                ft.Text("Vendas", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Nova receita",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: open_quick_sale(self.app, pid),
                    style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                ),
                ft.OutlinedButton(
                    "Novo cliente",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=lambda _: open_client_modal(self.app, pid),
                ),
            ],
            spacing=8,
        )

        client_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(r["name"], color=ft.Colors.WHITE)),
                ft.DataCell(ft.Text(str(r["count"]), color=ft.Colors.GREY_400)),
                ft.DataCell(ft.Text(format_brl(r["total"]), color="#22C55E")),
            ])
            for r in by_client
        ] or [ft.DataRow(cells=[ft.DataCell(ft.Text("Nenhuma receita no ano", color=ft.Colors.GREY_500))] * 3)]

        client_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cliente / Tomador")),
                ft.DataColumn(ft.Text("Lançamentos")),
                ft.DataColumn(ft.Text("Total ano"), numeric=True),
            ],
            rows=client_rows,
            heading_row_color="#0F172A",
        )

        cadastro_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c.name, color=ft.Colors.WHITE)),
                ft.DataCell(ft.Text(c.document or "—", color=ft.Colors.GREY_400)),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#EF4444",
                                          on_click=lambda e, cid=c.id: delete_client(self.app, cid))),
            ])
            for c in clients
        ] or [ft.DataRow(cells=[ft.DataCell(ft.Text("Nenhum cliente", color=ft.Colors.GREY_500))] * 3)]

        recent_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(t.date.strftime("%d/%m/%Y"))),
                ft.DataCell(ft.Text(t.description[:40], color=ft.Colors.WHITE)),
                ft.DataCell(ft.Text(format_brl(t.amount), color="#22C55E")),
            ])
            for t in recent
        ]

        return ft.Column(
            [
                header,
                ft.Container(height=16),
                section_card("Receita por cliente (ano)", client_table),
                ft.Container(height=12),
                section_card("Clientes cadastrados", ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("Nome")), ft.DataColumn(ft.Text("Doc")), ft.DataColumn(ft.Text(""))],
                    rows=cadastro_rows,
                    heading_row_color="#0F172A",
                )),
                ft.Container(height=12),
                section_card("Últimas receitas", ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("Data")), ft.DataColumn(ft.Text("Descrição")), ft.DataColumn(ft.Text("Valor"))],
                    rows=recent_rows or [ft.DataRow(cells=[ft.DataCell(ft.Text("—"))] * 3)],
                    heading_row_color="#0F172A",
                ) if recent_rows else section_card("Últimas receitas", ft.Text("Nenhuma receita", color=ft.Colors.GREY_500))),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )