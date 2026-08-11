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
    scale_max: float | None = None,
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
    max_val = float(scale_max) if scale_max is not None else (max(values) if values else 1.0)
    if max_val <= 0:
        max_val = 1.0

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
                subtitle=str(item.get("subtitle") or ""),
                stacked=stacked_labels,
            )
        )

    return ft.Column(rows, spacing=12, tight=True)


def category_share_items(
    categories: list,
    *,
    max_items: int = 6,
    others_label: str | None = None,
) -> tuple[list[dict], float]:
    """Pure: top N + Others share rows. Values sum to period total."""
    ranked = sorted(categories, key=lambda c: float(c.get("total") or 0), reverse=True)
    total = sum(float(c.get("total") or 0) for c in ranked)
    head = ranked[:max_items]
    tail = ranked[max_items:]
    rows = list(head)
    if tail:
        other_total = sum(float(c.get("total") or 0) for c in tail)
        if other_total > 0:
            rows.append(
                {
                    "name": others_label or t("dash.chart_others"),
                    "icon": "⋯",
                    "total": other_total,
                }
            )

    items: list[dict] = []
    for c in rows:
        val = float(c.get("total") or 0)
        pct = (val / total * 100.0) if total > 0 else 0.0
        items.append(
            {
                "label": f"{c.get('icon', '')} {c.get('name', '')}".strip(),
                "value": val,
                "color": EXPENSE_COLOR,
                "subtitle": f"{pct:.0f}%",
                "pct": pct,
            }
        )
    return items, total


def _comparison_footer(
    *,
    expense_change_pct: float | None = None,
    income_change_pct: float | None = None,
) -> ft.Control | None:
    """Compact vs-previous-period line for chart footers."""
    from ui.theme import format_change

    bits: list[str] = []
    if expense_change_pct is not None:
        bits.append(t("dash.vs_prev_expense", change=format_change(expense_change_pct)))
    if income_change_pct is not None:
        bits.append(t("dash.vs_prev_income", change=format_change(income_change_pct)))
    if not bits:
        return None
    text = " · ".join(bits)
    return ft.Text(
        text,
        size=12,
        color=theme_colors().text_muted,
        weight=ft.FontWeight.W_500,
        tooltip=text,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )


def category_breakdown_chart(
    categories: list,
    *,
    max_items: int = 6,
    expense_change_pct: float | None = None,
) -> ft.Control:
    """Expense share bars: % of period total, top N + Others (hero-friendly)."""
    if not categories:
        return ft.Container(
            content=_empty_chart_text(t("personal.empty_no_expenses")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    items, total = category_share_items(categories, max_items=max_items)
    chart = horizontal_bar_chart(
        items,
        max_items=len(items),
        stacked_labels=True,
        scale_max=total if total > 0 else None,
    )
    header = ft.Row(
        [
            ft.Text(
                t("dash.expenses_total", amount=format_brl(total)),
                size=12,
                color=theme_colors().text_muted,
                weight=ft.FontWeight.W_500,
                tooltip=t("dash.expenses_total", amount=format_brl(total)),
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )
    footer = _comparison_footer(expense_change_pct=expense_change_pct)
    controls: list[ft.Control] = [header, chart]
    if footer is not None:
        controls.append(footer)
    return ft.Column(controls, spacing=10, tight=True)


def income_expense_chart(
    monthly_series: list,
    *,
    compact: bool = False,
    max_months: int = 6,
    expense_change_pct: float | None = None,
    income_change_pct: float | None = None,
) -> ft.Control:
    """Grouped income vs expense bars per month; optional vs-previous footer."""
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
    c = theme_colors()

    if compact:
        rows = []
        for point in subset:
            label = chart_point_label(point)
            income = float(point.get("income", 0))
            expense = float(point.get("expense", 0))
            net = income - expense
            net_color = c.success if net >= 0 else c.danger
            net_tip = t("dash.month_net", amount=format_brl(net))
            rows.append(
                ft.Row(
                    [
                        _axis_label(label, width=64, max_lines=1),
                        ft.Container(
                            content=_mini_bar(income, max_val, INCOME_COLOR, format_brl(income)),
                            expand=True,
                            tooltip=f"{t('personal.income')}: {format_brl(income)}",
                        ),
                        ft.Container(
                            content=_mini_bar(expense, max_val, EXPENSE_COLOR, format_brl(expense)),
                            expand=True,
                            tooltip=f"{t('personal.expense')}: {format_brl(expense)}",
                        ),
                        ft.Text(
                            format_brl(net),
                            size=12,
                            color=net_color,
                            weight=ft.FontWeight.W_600,
                            width=88,
                            text_align=ft.TextAlign.RIGHT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=net_tip,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        header = ft.Row(
            [
                ft.Text("", width=64),
                ft.Text(t("personal.income"), size=12, color=INCOME_COLOR, weight=ft.FontWeight.W_600, expand=True),
                ft.Text(t("personal.expense"), size=12, color=EXPENSE_COLOR, weight=ft.FontWeight.W_600, expand=True),
                ft.Text(t("dash.net_short"), size=12, color=c.text_muted, weight=ft.FontWeight.W_600, width=88, text_align=ft.TextAlign.RIGHT),
            ],
        )
        body: list[ft.Control] = [header, *rows]
        footer = _comparison_footer(
            expense_change_pct=expense_change_pct,
            income_change_pct=income_change_pct,
        )
        if footer is not None:
            body.append(footer)
        return ft.Column(body, spacing=10, tight=True)

    rows = []
    for point in subset:
        label = chart_point_label(point)
        income = float(point.get("income", 0))
        expense = float(point.get("expense", 0))
        net = income - expense
        rows.append(
            ft.Column(
                [
                    _axis_label(label, size=12, max_lines=1),
                    _bar_row(t("personal.income"), income, max_val, INCOME_COLOR, format_brl(income), stacked=False),
                    _bar_row(t("personal.expense"), expense, max_val, EXPENSE_COLOR, format_brl(expense), stacked=False),
                    ft.Text(
                        t("dash.month_net", amount=format_brl(net)),
                        size=12,
                        color=c.success if net >= 0 else c.danger,
                        weight=ft.FontWeight.W_500,
                        tooltip=t("dash.month_net", amount=format_brl(net)),
                    ),
                ],
                spacing=4,
                tight=True,
            )
        )

    body = list(rows)
    footer = _comparison_footer(
        expense_change_pct=expense_change_pct,
        income_change_pct=income_change_pct,
    )
    if footer is not None:
        body.append(footer)
    return ft.Column(body, spacing=8, tight=True)
