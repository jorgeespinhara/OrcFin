"""Holdings table for the investments screen."""

from __future__ import annotations

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.investment_holdings import delete_holding
from core.domain.br_date import format_br_date
from core.domain.value_objects.money import format_brl
from ui.investments.form import open_holding_form
from ui.theme import active as theme_colors


def build_holdings_table(items: list[dict], app, *, on_reload) -> ft.Control:
    c = theme_colors()
    col_style = ft.TextStyle(color=c.text_primary, weight=ft.FontWeight.W_600, size=12)
    cell_style = ft.TextStyle(color=c.text_primary, size=12)
    muted_style = ft.TextStyle(color=c.text_muted, size=12)

    columns = [
        ft.DataColumn(ft.Text("Tipo", style=col_style)),
        ft.DataColumn(ft.Text("Ativo", style=col_style)),
        ft.DataColumn(ft.Text("Nome", style=col_style)),
        ft.DataColumn(ft.Text("Data", style=col_style)),
        ft.DataColumn(ft.Text("Qtd", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("PM", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("Cota", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("Valor", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("Resultado", style=col_style), numeric=True),
        ft.DataColumn(ft.Text("", style=col_style)),
    ]

    rows: list[ft.DataRow] = []
    for item in items:
        holding = item["holding"]
        pnl_color = "#22C55E" if item["pnl"] >= 0 else "#EF4444"
        price_txt = format_brl(item["price"]) if item["has_quote"] else "n/d"
        value_txt = format_brl(item["market_value"]) if item["has_quote"] else "n/d"
        identifier = holding.symbol or holding.cnpj or EMPTY_CELL

        def edit(_e, h=holding):
            open_holding_form(app, holding=h, on_saved=on_reload)

        def remove(_e, hid=holding.id):
            delete_holding(hid)
            app.show_snack("Posição removida.")
            on_reload()

        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(item["asset_class_label"], style=cell_style)),
                    ft.DataCell(ft.Text(identifier, style=cell_style)),
                    ft.DataCell(ft.Text(holding.name, style=cell_style, max_lines=2)),
                    ft.DataCell(ft.Text(format_br_date(holding.applied_at) or EMPTY_CELL, style=muted_style)),
                    ft.DataCell(ft.Text(str(holding.quantity), style=cell_style)),
                    ft.DataCell(ft.Text(format_brl(holding.avg_cost), style=cell_style)),
                    ft.DataCell(ft.Text(price_txt, style=cell_style)),
                    ft.DataCell(ft.Text(value_txt, style=cell_style)),
                    ft.DataCell(
                        ft.Text(
                            f"{item['pnl_pct']:+.1f}% ({format_brl(item['pnl'])})"
                            if item["has_quote"]
                            else "n/d",
                            style=ft.TextStyle(color=pnl_color if item["has_quote"] else c.text_muted, size=12),
                        )
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.EDIT_OUTLINED,
                                    icon_size=18,
                                    icon_color="#14B8A6",
                                    tooltip="Editar",
                                    on_click=edit,
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_size=18,
                                    icon_color="#EF4444",
                                    tooltip="Excluir",
                                    on_click=remove,
                                ),
                            ],
                            spacing=0,
                            tight=True,
                        )
                    ),
                ]
            )
        )

    table = ft.DataTable(
        columns=columns,
        rows=rows,
        heading_row_color=c.surface_alt,
        data_row_color={"hovered": c.surface_alt},
        border=None,
        column_spacing=12,
        horizontal_lines=ft.border.BorderSide(0.5, c.border),
    )
    return ft.Row([table], scroll=ft.ScrollMode.AUTO, vertical_alignment=ft.CrossAxisAlignment.START)