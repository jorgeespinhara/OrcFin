"""Chart formatting helpers."""

from __future__ import annotations

import flet as ft

from ui.theme import active as theme_colors


def _muted_bar() -> str:
    return theme_colors().border


def readable_label(
    text: str,
    *,
    size: int = 13,
    weight=ft.FontWeight.W_600,
    color: str | None = None,
    expand: bool = False,
    width: int | None = None,
    max_lines: int = 2,
    muted: bool = False,
) -> ft.Text:
    """Label that prefers wrapping over hard truncation; full text in tooltip."""
    c = theme_colors()
    label = (text or "").strip()
    return ft.Text(
        label,
        size=size,
        width=width,
        expand=expand,
        max_lines=max_lines,
        overflow=ft.TextOverflow.ELLIPSIS,
        tooltip=label if label else None,
        color=color or (c.text_muted if muted else c.text_primary),
        weight=weight,
    )


def _axis_label(
    text: str,
    *,
    size: int = 14,
    width: int | None = None,
    expand: bool = False,
    max_lines: int = 2,
) -> ft.Text:
    return readable_label(
        text,
        size=size,
        width=width,
        expand=expand,
        max_lines=max_lines,
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
    """Chart area with optional fixed height. Avoid expand inside scroll parents."""
    if height is None:
        return ft.Container(content=content)
    if scroll:
        return ft.Container(
            content=ft.Column([content], scroll=ft.ScrollMode.AUTO, spacing=0, tight=True),
            height=height,
        )
    return ft.Container(content=content, height=height)


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
                        readable_label(title, size=15, expand=True, max_lines=2),
                        action or ft.Container(),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                _chart_body(content, height=height, scroll=scroll_content),
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=c.surface,
        border_radius=12,
        padding=16,
        border=ft.Border.all(1, c.border),
        # Only expand horizontally in rows; never fight parent scroll height.
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
                size=13,
                color=theme_colors().text_primary,
                weight=ft.FontWeight.W_600,
                width=100,
                text_align=ft.TextAlign.RIGHT,
                max_lines=1,
                tooltip=value_text,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def vertical_bar(
    value: float,
    max_value: float,
    color: str,
    *,
    chart_height: int = 160,
    bar_width: int = 22,
    label: str | None = None,
    show_value: bool = True,
) -> ft.Control:
    """Column bar growing upward — for time-series / comparison charts."""
    from core.domain.value_objects.money import format_brl

    magnitude = abs(float(value))
    peak = max(float(max_value), 1.0)
    bar_height = max(4, int((magnitude / peak) * chart_height))
    tip = label or format_brl(value)
    c = theme_colors()
    parts: list[ft.Control] = []
    if show_value:
        parts.append(
            ft.Text(
                format_brl(value),
                size=10,
                color=c.text_primary,
                weight=ft.FontWeight.W_600,
                text_align=ft.TextAlign.CENTER,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=tip,
                width=max(bar_width + 16, 56),
            )
        )
    parts.append(
        ft.Container(
            height=chart_height,
            width=bar_width + 8,
            alignment=ft.Alignment(0, 1),
            content=ft.Container(
                height=bar_height,
                width=bar_width,
                bgcolor=color,
                border_radius=5,
                tooltip=tip,
            ),
            tooltip=tip,
        )
    )
    return ft.Column(
        parts,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
        tight=True,
    )


def composition_bar(
    segments: list[dict],
    *,
    height: int = 28,
) -> ft.Control:
    """100% stacked horizontal strip (part-to-whole). Each segment: value, color, label."""
    c = theme_colors()
    total = sum(float(s.get("value") or 0) for s in segments) or 1.0
    cells: list[ft.Control] = []
    for s in segments:
        val = float(s.get("value") or 0)
        if val <= 0:
            continue
        weight = max(1, round((val / total) * 100))
        pct = val / total * 100
        tip = f"{s.get('label', '')}: {pct:.0f}%"
        cells.append(
            ft.Container(
                expand=weight,
                height=height,
                bgcolor=s.get("color") or c.accent,
                tooltip=tip,
            )
        )
    if not cells:
        return ft.Container(height=height, bgcolor=c.border, border_radius=8)
    return ft.Container(
        content=ft.Row(cells, spacing=1),
        border_radius=8,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        height=height,
    )
