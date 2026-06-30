"""Time-series chart controls."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, PROJECTION_COLOR, INCOME_COLOR, EXPENSE_COLOR
from ui.personal.charts.helpers import _axis_label, _empty_chart_text, _legend_label
from ui.personal.charts.bars import _bar_row

def _vertical_bar(
    value: float,
    max_value: float,
    color: str,
    *,
    chart_height: int = 200,
    bar_width: int = 28,
    dashed: bool = False,
) -> ft.Column:
    magnitude = abs(value)
    bar_height = max(10, int((magnitude / max_value) * chart_height)) if max_value > 0 else 10
    bar_bg = color if not dashed else f"{color}99"
    border = ft.Border.all(1, color) if dashed else None

    return ft.Column(
        [
            ft.Text(
                format_brl(value),
                size=12,
                color=theme_colors().text_primary,
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER,
                max_lines=1,
            ),
            ft.Container(
                height=chart_height,
                alignment=ft.Alignment(0, 1),
                content=ft.Container(
                    height=bar_height,
                    width=bar_width,
                    bgcolor=bar_bg,
                    border_radius=6,
                    border=border,
                ),
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

def balance_evolution_chart(
    evolution: list,
    *,
    projection_points: list | None = None,
    show_income_expense: bool = False,
) -> ft.Control:
    if not evolution and not projection_points:
        return ft.Container(
            content=_empty_chart_text("Histórico insuficiente para gráfico"),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    all_points = list(evolution) + list(projection_points or [])
    values = [float(p.get("cumulative_balance", p.get("projected_cumulative", 0))) for p in all_points]
    max_val = max(values) if values else 1.0
    if max_val <= 0:
        max_val = 1.0

    rows = []
    for point in evolution:
        val = float(point["cumulative_balance"])
        subtitle = ""
        if show_income_expense:
            subtitle = f"+{format_brl(point.get('income', 0))} / -{format_brl(point.get('expense', 0))}"
        rows.append(
            _bar_row(
                chart_point_label(point),
                abs(val),
                max_val,
                PERSONAL_ACCENT,
                format_brl(val),
                subtitle=subtitle,
            )
        )

    for point in projection_points or []:
        val = float(point.get("projected_cumulative", 0))
        rows.append(
            _bar_row(
                chart_point_label(point) if point.get("year") else point.get("label", f"+{point.get('month_offset', '')}m"),
                abs(val),
                max_val,
                PROJECTION_COLOR,
                format_brl(val),
                dashed=True,
                subtitle="projeção",
            )
        )

    legend = ft.Row(
        [
            ft.Container(width=14, height=14, bgcolor=PERSONAL_ACCENT, border_radius=3),
            _legend_label("Realizado"),
            ft.Container(width=14, height=14, bgcolor=PROJECTION_COLOR, border_radius=3),
            _legend_label("Projetado"),
        ],
        spacing=8,
    ) if projection_points else ft.Container()

    return ft.Column([legend, *rows], spacing=10)
def _projection_chart_sizing(month_count: int) -> tuple[int, int, int]:
    """Return chart height, bar width, and group spacing for N months."""
    count = max(1, month_count)
    chart_height = 200
    bar_width = max(14, min(36, int(900 / (count * 3.8))))
    group_spacing = max(6, min(14, int(18 - count * 0.8)))
    return chart_height, bar_width, group_spacing

def projection_forecast_chart(monthly_points: list) -> ft.Control:
    """Vertical grouped bars: months on horizontal axis, values upward."""
    if not monthly_points:
        return ft.Container(
            content=ft.Text(
                "Cadastre receitas e despesas para gerar a projeção",
                color=theme_colors().text_muted,
                size=14,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    chart_height, bar_width, bar_spacing = _projection_chart_sizing(len(monthly_points))
    max_val = max(
        max(float(p.get("income", 0)) for p in monthly_points),
        max(float(p.get("expense", 0)) for p in monthly_points),
        max(abs(float(p.get("net_savings", 0))) for p in monthly_points),
        1.0,
    )

    month_groups = []
    for point in monthly_points:
        label = chart_point_label(point)
        income = float(point.get("income", 0))
        expense = float(point.get("expense", 0))
        net = float(point.get("net_savings", 0))
        net_color = PROJECTION_COLOR if net >= 0 else "#EF4444"

        month_groups.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            _vertical_bar(
                                income, max_val, INCOME_COLOR,
                                chart_height=chart_height, bar_width=bar_width, dashed=True,
                            ),
                            _vertical_bar(
                                expense, max_val, EXPENSE_COLOR,
                                chart_height=chart_height, bar_width=bar_width, dashed=True,
                            ),
                            _vertical_bar(
                                net, max_val, net_color,
                                chart_height=chart_height, bar_width=bar_width, dashed=True,
                            ),
                        ],
                        spacing=bar_spacing,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    _axis_label(label),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                expand=True,
            )
        )

    legend = ft.Row(
        [
            ft.Container(width=14, height=14, bgcolor=INCOME_COLOR, border_radius=3),
            _legend_label("Receita"),
            ft.Container(width=14, height=14, bgcolor=EXPENSE_COLOR, border_radius=3),
            _legend_label("Despesa"),
            ft.Container(width=14, height=14, bgcolor=PROJECTION_COLOR, border_radius=3),
            _legend_label("Saldo +"),
            ft.Container(width=14, height=14, bgcolor="#EF4444", border_radius=3),
            _legend_label("Saldo −"),
        ],
        spacing=10,
        wrap=True,
    )

    return ft.Column(
        [
            legend,
            ft.Container(
                content=ft.Row(
                    month_groups,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    expand=True,
                ),
                border=ft.Border.only(top=ft.BorderSide(1, theme_colors().border)),
                padding=ft.Padding.only(top=16, bottom=8),
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
    )
