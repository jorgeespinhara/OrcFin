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
    _legend_label,
    _mini_bar,
    _muted_bar,
    composition_bar,
    readable_label,
    vertical_bar,
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


def _category_palette() -> list[str]:
    c = theme_colors()
    return [
        c.expense,
        c.accent,
        c.accent_portfolio,
        c.accent_card,
        c.warning,
        c.success,
        c.accent_soft,
        c.text_muted,
    ]


def category_breakdown_chart(
    categories: list,
    *,
    max_items: int = 6,
    expense_change_pct: float | None = None,
) -> ft.Control:
    """Part-to-whole composition strip + ranked legend (not a wall of H-bars)."""
    if not categories:
        return ft.Container(
            content=_empty_chart_text(t("personal.empty_no_expenses")),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    items, total = category_share_items(categories, max_items=max_items)
    palette = _category_palette()
    segments = []
    legend_rows: list[ft.Control] = []
    c = theme_colors()
    for i, item in enumerate(items):
        color = palette[i % len(palette)]
        segments.append(
            {"value": item["value"], "color": color, "label": item["label"]}
        )
        legend_rows.append(
            ft.Row(
                [
                    ft.Container(width=12, height=12, bgcolor=color, border_radius=3),
                    readable_label(item["label"], size=13, expand=True, max_lines=1),
                    ft.Text(
                        f"{item['pct']:.0f}%",
                        size=12,
                        color=c.text_muted,
                        width=40,
                        text_align=ft.TextAlign.RIGHT,
                        tooltip=f"{item['pct']:.0f}%",
                    ),
                    ft.Text(
                        format_brl(item["value"]),
                        size=13,
                        color=c.text_primary,
                        weight=ft.FontWeight.W_600,
                        width=100,
                        text_align=ft.TextAlign.RIGHT,
                        tooltip=format_brl(item["value"]),
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    header = ft.Row(
        [
            ft.Text(
                t("dash.expenses_total", amount=format_brl(total)),
                size=12,
                color=c.text_muted,
                weight=ft.FontWeight.W_500,
                tooltip=t("dash.expenses_total", amount=format_brl(total)),
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )
    controls: list[ft.Control] = [
        header,
        composition_bar(segments, height=32),
        ft.Column(legend_rows, spacing=8, tight=True),
    ]
    footer = _comparison_footer(expense_change_pct=expense_change_pct)
    if footer is not None:
        controls.append(footer)
    return ft.Column(controls, spacing=12, tight=True)


def income_expense_chart(
    monthly_series: list,
    *,
    compact: bool = False,
    max_months: int = 6,
    expense_change_pct: float | None = None,
    income_change_pct: float | None = None,
) -> ft.Control:
    """Income vs expense: vertical grouped columns by month (time on X)."""
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
    n = len(subset)
    # compact = denser columns (dashboard); non-compact = taller labels
    chart_h = 120 if compact else 160
    bar_w = max(10, min(22, int(360 / max(n * 2.2, 1))))

    groups: list[ft.Control] = []
    for point in subset:
        label = chart_point_label(point)
        income = float(point.get("income", 0))
        expense = float(point.get("expense", 0))
        net = income - expense
        groups.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            vertical_bar(
                                income,
                                max_val,
                                INCOME_COLOR,
                                chart_height=chart_h,
                                bar_width=bar_w,
                                label=f"{t('personal.income')}: {format_brl(income)}",
                                show_value=False,
                            ),
                            vertical_bar(
                                expense,
                                max_val,
                                EXPENSE_COLOR,
                                chart_height=chart_h,
                                bar_width=bar_w,
                                label=f"{t('personal.expense')}: {format_brl(expense)}",
                                show_value=False,
                            ),
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    _axis_label(label, size=10, max_lines=1),
                    ft.Text(
                        format_brl(net),
                        size=10,
                        color=c.success if net >= 0 else c.danger,
                        weight=ft.FontWeight.W_600,
                        tooltip=t("dash.month_net", amount=format_brl(net)),
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                tight=True,
            )
        )

    legend = ft.Row(
        [
            ft.Container(width=12, height=12, bgcolor=INCOME_COLOR, border_radius=3),
            _legend_label(t("personal.income")),
            ft.Container(width=12, height=12, bgcolor=EXPENSE_COLOR, border_radius=3),
            _legend_label(t("personal.expense")),
        ],
        spacing=8,
    )
    body: list[ft.Control] = [
        legend,
        ft.Container(
            content=ft.Row(
                groups,
                spacing=max(4, min(10, int(14 - n * 0.4))),
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                vertical_alignment=ft.CrossAxisAlignment.END,
                scroll=ft.ScrollMode.AUTO if n > 8 else None,
            ),
            border=ft.Border.only(top=ft.BorderSide(1, c.border)),
            padding=ft.Padding.only(top=12, bottom=4),
        ),
    ]
    footer = _comparison_footer(
        expense_change_pct=expense_change_pct,
        income_change_pct=income_change_pct,
    )
    if footer is not None:
        body.append(footer)
    return ft.Column(body, spacing=8, tight=True)
