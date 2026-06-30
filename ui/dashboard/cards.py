"""Dashboard summary and KPI cards."""

from __future__ import annotations

import flet as ft

def build_summary_card(
    self, title: str, value: str, subtitle: str, icon: str, accent_color: str
    ) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon, color=accent_color, size=22),
                        ft.Text(title, size=13, color=theme_colors().text_muted, weight=ft.FontWeight.W_500),
                    ],
                    spacing=8,
                ),
                ft.Text(value, size=26, weight=ft.FontWeight.BOLD, color=theme_colors().text_primary),
                ft.Text(subtitle, size=11, color=theme_colors().text_muted),
            ],
            spacing=4,
        ),
        padding=20,
        bgcolor=theme_colors().surface,
        border_radius=16,
        width=280,
        height=120,
        border=ft.Border.all(1, "#334155"),
    )

def build_projection_metric_card(
    self, title: str, value: str, subtitle: str, icon: str, accent_color: str
    ) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(icon, color=accent_color, size=28),
                        ft.Text(title, size=14, color=theme_colors().text_secondary, weight=ft.FontWeight.W_500, expand=True),
                    ],
                    spacing=10,
                ),
                ft.Text(value, size=34, weight=ft.FontWeight.BOLD, color=theme_colors().text_primary),
                ft.Text(subtitle, size=12, color=theme_colors().text_muted),
            ],
            spacing=6,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=ft.Border.all(1, "#334155"),
        expand=True,
        height=150,
    )

def format_change(view, pct: float) -> str:
    if pct > 0:
        return f"+{pct:.1f}% vs período anterior"
    elif pct < 0:
        return f"{pct:.1f}% vs período anterior"
    return "Sem variação"

def mini_patrimony(view, label: str, value: str, color: str) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, size=11, color=theme_colors().text_muted),
            ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color),
        ],
        spacing=4,
    )
