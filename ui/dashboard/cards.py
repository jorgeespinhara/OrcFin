"""Dashboard summary and KPI cards."""

from __future__ import annotations

import flet as ft

from ui.theme import active as theme_colors, format_change

__all__ = [
    "build_summary_card",
    "build_projection_metric_card",
    "format_change",
    "mini_patrimony",
]


def build_summary_card(
    title: str, value: str, subtitle: str, icon: str, accent_color: str
) -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Column(
            [
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
            ],
            spacing=4,
            tight=True,
        ),
        padding=16,
        bgcolor=c.surface,
        border_radius=16,
        width=260,
        height=120,
        border=ft.Border.all(1, c.border),
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
