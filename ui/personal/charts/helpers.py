"""Chart formatting helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, INCOME_COLOR, EXPENSE_COLOR, PROJECTION_COLOR

def _muted_bar() -> str:
    return theme_colors().border

def _axis_label(text: str, *, size: int = 14, width: int | None = None) -> ft.Text:
    return ft.Text(
        text,
        size=size,
        width=width,
        color=theme_colors().text_primary,
        weight=ft.FontWeight.W_600,
    )

def _legend_label(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=12,
        color=theme_colors().text_primary,
        weight=ft.FontWeight.W_500,
    )

def _empty_chart_text(message: str, *, size: int = 12) -> ft.Text:
    return ft.Text(message, color=theme_colors().text_muted, size=size)

def _chart_body(
    content: ft.Control,
    height: int | None = None,
    *,
    scroll: bool = True,
) -> ft.Container:
    """Fixed-height chart area; scrolls when content overflows."""
    if height is None:
        return ft.Container(content=content, expand=scroll)
    if scroll:
        return ft.Container(
            content=ft.Column([content], scroll=ft.ScrollMode.AUTO, spacing=0),
            height=height,
        )
    return ft.Container(content=content, height=height, expand=True)

def section_card(
    title: str,
    content: ft.Control,
    action: ft.Control | None = None,
    *,
    expand: bool = False,
    height: int | None = None,
    scroll_content: bool = True,
) -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=c.text_primary),
                        ft.Container(expand=True),
                        action or ft.Container(),
                    ],
                ),
                _chart_body(content, height=height, scroll=scroll_content),
            ],
            spacing=10,
            expand=expand,
        ),
        bgcolor=c.surface,
        border_radius=12,
        padding=16,
        border=ft.Border.all(1, c.border),
        expand=expand,
    )

def _mini_bar(value: float, max_value: float, color: str, value_text: str) -> ft.Control:
    fill_ratio = max(0.04, min(1.0, value / max_value)) if max_value > 0 else 0.04
    filled_weight = max(1, round(fill_ratio * 100))
    empty_weight = max(1, 100 - filled_weight)
    return ft.Row(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            height=14,
                            bgcolor=color,
                            border_radius=5,
                            expand=filled_weight,
                        ),
                        ft.Container(height=14, expand=empty_weight),
                    ],
                    spacing=0,
                ),
                bgcolor=_muted_bar(),
                border_radius=5,
                height=14,
                expand=True,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
            ft.Text(
                value_text,
                size=14,
                color=theme_colors().text_primary,
                weight=ft.FontWeight.W_600,
                width=108,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
