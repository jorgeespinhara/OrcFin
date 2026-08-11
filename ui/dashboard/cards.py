"""Dashboard summary and KPI cards."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

import flet as ft

from ui.theme import active as theme_colors, format_change

__all__ = [
    "build_summary_card",
    "build_spendable_card",
    "build_projection_metric_card",
    "build_net_worth_strip",
    "format_change",
    "mini_patrimony",
    "mini_sparkline",
]


def mini_sparkline(
    values: Sequence[float],
    color: str,
    *,
    height: int = 28,
    width: int = 88,
) -> ft.Control:
    """Compact bar sparkline for KPI trend context (needs ≥2 points)."""
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 2:
        return ft.Container(height=0, width=0)
    peak = max(abs(v) for v in nums) or 1.0
    bars = []
    bar_w = max(3, (width - (len(nums) - 1) * 2) // len(nums))
    for v in nums:
        h = max(3, int((abs(v) / peak) * height))
        bars.append(
            ft.Container(
                width=bar_w,
                height=h,
                bgcolor=color if v >= 0 else theme_colors().danger,
                border_radius=2,
                opacity=0.85 if v >= 0 else 0.7,
            )
        )
    return ft.Container(
        content=ft.Row(
            bars,
            spacing=2,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        height=height,
        width=width,
        alignment=ft.Alignment(1, 1),
    )


def build_summary_card(
    title: str,
    value: str,
    subtitle: str,
    icon: str,
    accent_color: str,
    *,
    on_click: Callable | None = None,
    tooltip: str | None = None,
    sparkline_values: Sequence[float] | None = None,
) -> ft.Container:
    c = theme_colors()
    nums = [float(v) for v in (sparkline_values or []) if v is not None]
    show_spark = len(nums) >= 2
    body: list[ft.Control] = [
        ft.Row(
            [
                ft.Icon(icon, color=accent_color, size=22),
                ft.Text(
                    title,
                    size=13,
                    color=c.text_muted,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=title,
                ),
            ],
            spacing=8,
        ),
        ft.Text(
            value,
            size=24,
            weight=ft.FontWeight.BOLD,
            color=c.text_primary,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=value,
        ),
        ft.Text(
            subtitle,
            size=12,
            color=c.text_muted,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=subtitle,
        ),
    ]
    if show_spark:
        body.append(mini_sparkline(nums, accent_color))

    return ft.Container(
        content=ft.Column(body, spacing=4, tight=True),
        padding=16,
        bgcolor=c.surface,
        border_radius=16,
        width=260,
        height=148 if show_spark else 120,
        border=ft.Border.all(1, c.border),
        on_click=on_click,
        ink=bool(on_click),
        tooltip=tooltip,
    )


def build_spendable_card(
    value: str,
    spend: dict,
    *,
    on_click: Callable | None = None,
    tooltip: str | None = None,
) -> ft.Container:
    """Hero KPI: free-to-spend with bullet progress vs post-fixed pool."""
    c = theme_colors()
    accent = c.accent_portfolio
    income = Decimal(str(spend.get("income") or 0))
    recurring = Decimal(str(spend.get("recurring_fixed") or 0))
    margin = Decimal(str(spend.get("safety_margin") or 0))
    remaining = Decimal(str(spend.get("spendable") or 0))
    safety_pct = float(spend.get("safety_pct") or 0)

    pool = income - recurring - margin
    if pool < 0:
        pool = Decimal("0")
    ratio = float(remaining / pool) if pool > 0 else (1.0 if remaining > 0 else 0.0)
    ratio = max(0.0, min(1.0, ratio))

    from core.i18n import t

    if remaining <= 0:
        status = t("dash.spendable_gone")
        bar_color = c.danger
    elif ratio < 0.25:
        status = t("dash.spendable_low")
        bar_color = c.warning
    else:
        status = t("dash.spendable_ok")
        bar_color = accent

    subtitle = t("dash.spendable_sub", pct=f"{safety_pct:.0f}", status=status)

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SAVINGS, color=accent, size=22),
                        ft.Text(
                            t("dash.spendable_title"),
                            size=13,
                            color=c.text_muted,
                            weight=ft.FontWeight.W_500,
                            expand=True,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Text(
                    value,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=c.text_primary,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=value,
                ),
                ft.ProgressBar(
                    value=ratio,
                    color=bar_color,
                    bgcolor=c.border,
                    height=8,
                    border_radius=4,
                ),
                ft.Text(
                    subtitle,
                    size=12,
                    color=c.text_muted,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=subtitle,
                ),
            ],
            spacing=4,
            tight=True,
        ),
        padding=16,
        bgcolor=c.surface,
        border_radius=16,
        width=280,
        height=148,
        border=ft.Border.all(2, accent),
        on_click=on_click,
        ink=bool(on_click),
        tooltip=tooltip,
    )


def build_net_worth_strip(
    *,
    net_worth: str,
    assets: str,
    liabilities: str,
    sparkline_values: Sequence[float] | None = None,
    on_click: Callable | None = None,
    tooltip: str | None = None,
) -> ft.Container:
    """Compact net-worth strip: total, assets, liabilities, optional sparkline."""
    from core.i18n import t

    c = theme_colors()
    nums = [float(v) for v in (sparkline_values or []) if v is not None]
    spark = mini_sparkline(nums, c.accent, height=24, width=96) if len(nums) >= 2 else ft.Container()

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_BALANCE, color=c.accent, size=22),
                ft.Column(
                    [
                        ft.Text(
                            t("dash.net_worth"),
                            size=11,
                            color=c.text_muted,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            net_worth,
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=c.text_primary,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=net_worth,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
                ft.Container(width=16),
                mini_patrimony(t("dash.assets"), assets, c.success),
                ft.Container(width=12),
                mini_patrimony(t("dash.liabilities"), liabilities, c.danger),
                ft.Container(expand=True),
                spark,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(16, 12, 16, 12),
        bgcolor=c.surface,
        border_radius=12,
        border=ft.Border.all(1, c.border),
        on_click=on_click,
        ink=bool(on_click),
        tooltip=tooltip,
    )


def build_projection_metric_card(
    title: str, value: str, subtitle: str, icon: str, accent_color: str
) -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon, color=accent_color, size=28),
                        ft.Text(
                            title,
                            size=14,
                            color=c.text_secondary,
                            weight=ft.FontWeight.W_500,
                            expand=True,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=title,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Text(
                    value,
                    size=26,
                    weight=ft.FontWeight.BOLD,
                    color=c.text_primary,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=value,
                ),
                ft.Text(
                    subtitle,
                    size=12,
                    color=c.text_muted,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    tooltip=subtitle,
                ),
            ],
            spacing=6,
            tight=True,
        ),
        padding=20,
        bgcolor=c.surface,
        border_radius=16,
        border=ft.Border.all(1, c.border),
        expand=True,
        height=150,
    )


def mini_patrimony(label: str, value: str, color: str) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, size=12, color=theme_colors().text_muted, tooltip=label),
            ft.Text(
                value,
                size=18,
                weight=ft.FontWeight.BOLD,
                color=color,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=value,
            ),
        ],
        spacing=4,
        tight=True,
    )
