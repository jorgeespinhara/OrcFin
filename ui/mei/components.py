"""Reusable MEI UI components."""

from __future__ import annotations

import flet as ft

from ui.mei.constants import MEI_ACCENT
from ui.theme import active as theme_colors, field_params, dropdown_params

FIELD_HEIGHT = 56


def _mei_label_style() -> ft.TextStyle:
    c = theme_colors()
    return ft.TextStyle(color=c.text_primary, size=13)


def modal_field(**kwargs) -> ft.TextField:
    params = field_params(accent=MEI_ACCENT)
    params["label_style"] = _mei_label_style()
    params.setdefault("height", FIELD_HEIGHT)
    params.update(kwargs)
    return ft.TextField(**params)


def modal_dropdown(**kwargs) -> ft.Dropdown:
    params = dropdown_params(accent=MEI_ACCENT)
    params["label_style"] = _mei_label_style()
    params.setdefault("height", FIELD_HEIGHT)
    params.update(kwargs)
    return ft.Dropdown(**params)


def mei_title(text: str, size: int = 28) -> ft.Text:
    c = theme_colors()
    return ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=c.text_primary)


def mei_heading(text: str, size: int = 18) -> ft.Text:
    c = theme_colors()
    return ft.Text(text, size=size, weight=ft.FontWeight.W_600, color=c.text_primary)


def mei_text(text: str, *, size: int = 13, muted: bool = False, color: str | None = None, **kwargs) -> ft.Text:
    c = theme_colors()
    return ft.Text(
        text,
        size=size,
        color=color or (c.text_muted if muted else c.text_secondary),
        **kwargs,
    )


def mei_card(content: ft.Control, **kwargs) -> ft.Container:
    c = theme_colors()
    border = kwargs.pop("border", ft.Border.all(1, c.border))
    return ft.Container(
        content=content,
        bgcolor=kwargs.pop("bgcolor", c.surface),
        border_radius=kwargs.pop("border_radius", 12),
        padding=kwargs.pop("padding", 24),
        border=border,
        **kwargs,
    )


def mei_banner() -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.BUSINESS, color=MEI_ACCENT, size=20),
                ft.Text(
                    "Modo MEI: finanças da PJ separadas do pessoal",
                    color=c.mei_banner_text,
                    size=13,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=8,
        ),
        bgcolor=c.mei_banner_bg,
        border=ft.Border.all(1, MEI_ACCENT),
        border_radius=8,
        padding=12,
    )


def metric_card(label: str, value: str, color: str, icon: str | None = None) -> ft.Container:
    c = theme_colors()
    header = [
        ft.Icon(icon, color=color, size=20) if icon else ft.Container(),
        ft.Text(label, size=11, color=c.text_primary),
    ]
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(header, spacing=6) if icon else ft.Text(label, size=11, color=c.text_primary),
                ft.Text(value, size=22, weight=ft.FontWeight.BOLD, color=color),
            ],
            spacing=4,
        ),
        bgcolor=c.surface,
        border_radius=12,
        padding=16,
        expand=True,
        border=ft.Border.all(1, c.border),
    )


def section_card(title: str, content: ft.Control, action: ft.Control | None = None) -> ft.Container:
    c = theme_colors()
    header_row = ft.Row(
        [
            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=c.text_primary),
            ft.Container(expand=True),
            action or ft.Container(),
        ],
    )
    return ft.Container(
        content=ft.Column([header_row, content], spacing=12),
        bgcolor=c.surface,
        border_radius=12,
        padding=20,
        border=ft.Border.all(1, c.border),
    )