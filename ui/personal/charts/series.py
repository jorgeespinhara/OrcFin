"""Time-series chart controls."""

from __future__ import annotations

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from core.i18n import t
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, PROJECTION_COLOR, INCOME_COLOR, EXPENSE_COLOR
from ui.personal.charts.helpers import (
    _axis_label,
    _empty_chart_text,
    _legend_label,
    vertical_bar,
)


def _vertical_bar(
    value: float,
    max_value: float,
    color: str,
    *,
    chart_height: int = 200,
    bar_width: int = 28,
    dashed: bool = False,
) -> ft.Control:
    """Compat wrapper for projection chart."""
    _ = dashed
    return vertical_bar(
        value,
        max_value,
        color,
        chart_height=chart_height,
        bar_width=bar_width,
        show_value=True,
    )


def balance_evolution_chart(
    evolution: list,
    *,
    projection_points: list | None = None,
    show_income_expense: bool = False,
) -> ft.Control:
    """Vertical columns of cumulative balance over months (time on X)."""
    if not evolution and not projection_points:
        return ft.Container(
            content=_empty_chart_text(t("personal.empty_history_chart")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    all_points = list(evolution) + list(projection_points or [])
    values = [
        abs(float(p.get("cumulative_balance", p.get("projected_cumulative", 0))))
        for p in all_points
    ]
    max_val = max(values) if values else 1.0
    if max_val <= 0:
        max_val = 1.0

    n = max(len(all_points), 1)
    bar_w = max(12, min(28, int(420 / n)))
    chart_h = 150

    month_cols: list[ft.Control] = []
    for point in evolution:
        val = float(point["cumulative_balance"])
        color = PERSONAL_ACCENT if val >= 0 else theme_colors().danger
        label = chart_point_label(point)
        tip = format_brl(val)
        if show_income_expense:
            tip = (
                f"{tip} (+{format_brl(point.get('income', 0))} / "
                f"-{format_brl(point.get('expense', 0))})"
            )
        month_cols.append(
            ft.Column(
                [
                    vertical_bar(
                        val,
                        max_val,
                        color,
                        chart_height=chart_h,
                        bar_width=bar_w,
                        label=tip,
                        show_value=n <= 8,
                    ),
                    _axis_label(label, size=11, max_lines=1),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
                tight=True,
            )
        )

    for point in projection_points or []:
        val = float(point.get("projected_cumulative", 0))
        label = (
            chart_point_label(point)
            if point.get("year")
            else point.get("label", f"+{point.get('month_offset', '')}m")
        )
        month_cols.append(
            ft.Column(
                [
                    vertical_bar(
                        val,
                        max_val,
                        PROJECTION_COLOR,
                        chart_height=chart_h,
                        bar_width=bar_w,
                        label=format_brl(val),
                        show_value=n <= 8,
                    ),
                    _axis_label(str(label), size=11, max_lines=1),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
                tight=True,
            )
        )

    legend = (
        ft.Row(
            [
                ft.Container(width=12, height=12, bgcolor=PERSONAL_ACCENT, border_radius=3),
                _legend_label(t("personal.actual")),
                ft.Container(width=12, height=12, bgcolor=PROJECTION_COLOR, border_radius=3),
                _legend_label(t("personal.projected")),
            ],
            spacing=8,
        )
        if projection_points
        else ft.Container()
    )

    return ft.Column(
        [
            legend,
            ft.Container(
                content=ft.Row(
                    month_cols,
                    spacing=max(4, min(12, int(16 - n * 0.5))),
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    scroll=ft.ScrollMode.AUTO if n > 8 else None,
                ),
                border=ft.Border.only(top=ft.BorderSide(1, theme_colors().border)),
                padding=ft.Padding.only(top=12, bottom=4),
            ),
        ],
        spacing=8,
        tight=True,
    )


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
                t("personal.empty_projection"),
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
        net_color = PROJECTION_COLOR if net >= 0 else theme_colors().danger

        month_groups.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            _vertical_bar(
                                income,
                                max_val,
                                INCOME_COLOR,
                                chart_height=chart_height,
                                bar_width=bar_width,
                                dashed=True,
                            ),
                            _vertical_bar(
                                expense,
                                max_val,
                                EXPENSE_COLOR,
                                chart_height=chart_height,
                                bar_width=bar_width,
                                dashed=True,
                            ),
                            _vertical_bar(
                                net,
                                max_val,
                                net_color,
                                chart_height=chart_height,
                                bar_width=bar_width,
                                dashed=True,
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
            _legend_label(t("personal.income")),
            ft.Container(width=14, height=14, bgcolor=EXPENSE_COLOR, border_radius=3),
            _legend_label(t("personal.expense")),
            ft.Container(width=14, height=14, bgcolor=PROJECTION_COLOR, border_radius=3),
            _legend_label(t("personal.balance_pos")),
            ft.Container(width=14, height=14, bgcolor=theme_colors().danger, border_radius=3),
            _legend_label(t("personal.balance_neg")),
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
                ),
                border=ft.Border.only(top=ft.BorderSide(1, theme_colors().border)),
                padding=ft.Padding.only(top=16, bottom=8),
            ),
        ],
        spacing=12,
        tight=True,
    )
