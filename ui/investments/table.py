"""Holdings table for the investments screen."""

from __future__ import annotations

import flet as ft

from core.copy import EMPTY_CELL
from core.db.repositories.investment_holdings import delete_holding
from core.domain.br_date import format_br_date
from core.domain.value_objects.money import format_brl
from core.i18n import t
from ui.investments.form import open_holding_form
from ui.theme import active as theme_colors, signed_label, status_color


def _asset_class_label(asset_class: str) -> str:
    key = f"inv.asset.{asset_class}"
    label = t(key)
    return label if label != key else asset_class


def build_holdings_table(items: list[dict], app, *, on_reload) -> ft.Control:
    c = theme_colors()
    col_style = ft.TextStyle(color=c.text_primary, weight=ft.FontWeight.W_600, size=12)
    cell_style = ft.TextStyle(color=c.text_primary, size=12)
    muted_style = ft.TextStyle(color=c.text_muted, size=12)

    columns = [
        ft.DataColumn(ft.Text(t("inv.col.type"), style=col_style)),
        ft.DataColumn(ft.Text(t("inv.col.asset"), style=col_style)),
        ft.DataColumn(ft.Text(t("inv.col.name"), style=col_style)),
        ft.DataColumn(ft.Text(t("inv.col.date"), style=col_style)),
        ft.DataColumn(ft.Text(t("inv.col.qty"), style=col_style), numeric=True),
        ft.DataColumn(ft.Text(t("inv.col.avg"), style=col_style), numeric=True),
        ft.DataColumn(ft.Text(t("inv.col.quote"), style=col_style), numeric=True),
        ft.DataColumn(ft.Text(t("inv.col.value"), style=col_style), numeric=True),
        ft.DataColumn(ft.Text(t("inv.col.result"), style=col_style), numeric=True),
        ft.DataColumn(ft.Text("", style=col_style)),
    ]

    rows: list[ft.DataRow] = []
    for item in items:
        holding = item["holding"]
        pnl_color = status_color(positive=item["pnl"] >= 0)
        price_txt = format_brl(item["price"]) if item["has_quote"] else t("inv.na")
        value_txt = format_brl(item["market_value"]) if item["has_quote"] else t("inv.na")
        identifier = holding.symbol or holding.cnpj or EMPTY_CELL
        if item["has_quote"]:
            result_txt = f"{signed_label(float(item['pnl_pct']))} ({format_brl(item['pnl'])})"
        else:
            result_txt = t("inv.na")
        class_label = _asset_class_label(holding.asset_class)

        def edit(_e, h=holding):
            open_holding_form(app, holding=h, on_saved=on_reload)

        def remove(_e, hid=holding.id):
            delete_holding(hid)
            app.show_snack(t("inv.removed"))
            on_reload()

        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(class_label, style=cell_style)),
                    ft.DataCell(ft.Text(identifier, style=cell_style)),
                    ft.DataCell(ft.Text(holding.name, style=cell_style, max_lines=2)),
                    ft.DataCell(ft.Text(format_br_date(holding.applied_at) or EMPTY_CELL, style=muted_style)),
                    ft.DataCell(ft.Text(str(holding.quantity), style=cell_style)),
                    ft.DataCell(ft.Text(format_brl(holding.avg_cost), style=cell_style)),
                    ft.DataCell(ft.Text(price_txt, style=cell_style)),
                    ft.DataCell(ft.Text(value_txt, style=cell_style)),
                    ft.DataCell(
                        ft.Text(
                            result_txt,
                            style=ft.TextStyle(color=pnl_color if item["has_quote"] else c.text_muted, size=12),
                        )
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.EDIT_OUTLINED,
                                    icon_size=18,
                                    icon_color=c.accent,
                                    tooltip=t("inv.tip_edit"),
                                    on_click=edit,
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_size=18,
                                    icon_color=c.danger,
                                    tooltip=t("inv.tip_delete"),
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
