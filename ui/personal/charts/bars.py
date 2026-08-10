"""Bar chart controls for spending breakdown."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from core.i18n import t
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, INCOME_COLOR, EXPENSE_COLOR
from ui.personal.charts.helpers import (
    _axis_label,
    _empty_chart_text,
    _mini_bar,
    _muted_bar,
    readable_label,
)


def _bar_row(
    label: str,
    value: float,
    max_value: float,
    color: str,
    value_text: str,
    *,
    dashed: bool = False,
    subtitle: str = "",
    label_width: int | None = None,
    stacked: bool = True,
) -> ft.Control:
    """Bar with full label. Stacked layout keeps long category names readable."""
    bar_bg = _muted_bar() if not dashed else theme_colors().surface_alt
    bar_fg = color if not dashed else f"{color}88"
    border = ft.Border.all(1, color) if dashed else None
    fill_ratio = max(0.04, min(1.0, value / max_value)) if max_value > 0 else 0.04
    filled_weight = max(1, round(fill_ratio * 100))
    empty_weight = max(1, 100 - filled_weight)

    bar = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    height=14,
                    bgcolor=bar_fg,
                    border_radius=5,
                    border=border,
                    expand=filled_weight,
                ),
                ft.Container(height=14, expand=empty_weight),
            ],
            spacing=0,
        ),
        bgcolor=bar_bg,
        border_radius=5,
        height=14,
        expand=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    value_ctrl = ft.Text(
        value_text,
        size=13,
        color=theme_colors().text_primary,
        weight=ft.FontWeight.W_600,
        width=100,
        text_align=ft.TextAlign.RIGHT,
        max_lines=1,
        tooltip=value_text,
    )

    if stacked:
        return ft.Column(
            [
                readable_label(label, size=13, max_lines=2),
                ft.Text(subtitle, size=12, color=theme_colors().text_secondary, visible=bool(subtitle))
                if subtitle
                else ft.Container(height=0),
                ft.Row(
                    [bar, value_ctrl],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            tight=True,
        )

    # Compact inline row for short labels (Receita / Despesa / months)
    return ft.Column(
        [
            ft.Row(
                [
                    _axis_label(label, width=label_width or 88, max_lines=1),
                    bar,
                    value_ctrl,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(subtitle, size=12, color=theme_colors().text_secondary, visible=bool(subtitle))
            if subtitle
            else ft.Container(),
        ],
        spacing=4,
    )


def horizontal_bar_chart(
    items: Sequence[dict],
    *,
    value_key: str = "value",
    label_key: str = "label",
    color_key: str | None = "color",
    default_color: str = PERSONAL_ACCENT,
    format_value: Callable[[Decimal | float], str] | None = None,
    max_items: int = 10,
    empty_message: str | None = None,
    stacked_labels: bool = True,
) -> ft.Control:
    if not items:
        return ft.Container(
            content=_empty_chart_text(empty_message or t("personal.empty_no_data")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    fmt = format_value or (lambda v: format_brl(v))
    subset = list(items[:max_items])
    values = [float(item[value_key]) for item in subset]
    max_val = max(values) if values else 1.0

    rows = []
    for item in subset:
        val = float(item[value_key])
        color = item.get(color_key, default_color) if color_key else default_color
        label = str(item.get(label_key, "") or "").strip()
        rows.append(
            _bar_row(
                label,
                val,
                max_val,
                color,
                fmt(item[value_key]),
                stacked=stacked_labels,
            )
        )

    return ft.Column(rows, spacing=12, tight=True)


def category_breakdown_chart(categories: list) -> ft.Control:
    if not categories:
        return ft.Container(
            content=_empty_chart_text(t("personal.empty_no_expenses")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    items = [
        {
            "label": f"{c.get('icon', '')} {c['name']}".strip(),
            "value": c["total"],
            "color": EXPENSE_COLOR,
        }
        for c in categories
    ]
    return horizontal_bar_chart(items, max_items=8, stacked_labels=True)


def income_expense_chart(monthly_series: list, *, compact: bool = False, max_months: int = 6) -> ft.Control:
    """Grouped income vs expense bars per month."""
    if not monthly_series:
        return ft.Container(
            content=_empty_chart_text(t("personal.empty_history_short")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    subset = monthly_series[-max_months:]
    max_val = max(
        max(float(m.get("income", 0)) for m in subset),
        max(float(m.get("expense", 0)) for m in subset),
        1.0,
    )

    if compact:
        rows = []
        for point in subset:
            label = chart_point_label(point)
            income = float(point.get("income", 0))
            expense = float(point.get("expense", 0))
            rows.append(
                ft.Row(
                    [
                        _axis_label(label, width=72, max_lines=1),
                        ft.Container(
                            content=_mini_bar(income, max_val, INCOME_COLOR, format_brl(income)),
                            expand=True,
                        ),
                        ft.Container(
                            content=_mini_bar(expense, max_val, EXPENSE_COLOR, format_brl(expense)),
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        header = ft.Row(
            [
                ft.Text("", width=72),
                ft.Text(t("personal.income"), size=13, color=INCOME_COLOR, weight=ft.FontWeight.W_600, expand=True),
                ft.Text(t("personal.expense"), size=13, color=EXPENSE_COLOR, weight=ft.FontWeight.W_600, expand=True),
            ],
        )
        return ft.Column([header, *rows], spacing=10, tight=True)

    rows = []
    for point in subset:
        label = chart_point_label(point)
        income = float(point.get("income", 0))
        expense = float(point.get("expense", 0))
        rows.append(
            ft.Column(
                [
                    _axis_label(label, size=12, max_lines=1),
                    _bar_row(t("personal.income"), income, max_val, INCOME_COLOR, format_brl(income), stacked=False),
                    _bar_row(t("personal.expense"), expense, max_val, EXPENSE_COLOR, format_brl(expense), stacked=False),
                ],
                spacing=4,
                tight=True,
            )
        )

    return ft.Column(rows, spacing=8, tight=True)
