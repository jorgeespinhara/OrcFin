"""Reusable controls for settings sections."""

import flet as ft

from core.i18n import t

from ui.theme import (
    PERSONAL_ACCENT,
    active as theme_colors,
    body_text,
    danger_button_style,
    dropdown_params,
    field_params,
    on_surface_button_style,
    primary_button_style,
    section_style,
    switch_label_style,
    title_text,
)

__all__ = [
    "PROFILE_COLORS",
    "RESET_BULLETS_HEIGHT",
    "_ACCENT",
    "_action_button",
    "_danger_button",
    "_modal_dropdown",
    "_modal_field",
    "_modal_text",
    "body_text",
    "on_surface_button_style",
    "primary_button_style",
    "danger_button_style",
    "profile_modal_actions",
    "section_card",
    "switch_label_style",
    "theme_colors",
]

PROFILE_COLORS = [
    "#14B8A6",
    "#3B82F6",
    "#8B5CF6",
    "#F59E0B",
    "#EF4444",
    "#EC4899",
    "#10B981",
]
_ACCENT = PERSONAL_ACCENT


def _modal_text(text: str, **kwargs) -> ft.Text:
    color = kwargs.pop("color", theme_colors().text_primary)
    return ft.Text(text, color=color, **kwargs)


def _modal_field(**kwargs) -> ft.TextField:
    params = field_params(accent=_ACCENT)
    params.update(kwargs)
    return ft.TextField(**params)


def _modal_dropdown(**kwargs) -> ft.Dropdown:
    params = dropdown_params(accent=_ACCENT)
    params.update(kwargs)
    return ft.Dropdown(**params)


def section_card(content: ft.Control, **overrides) -> ft.Container:
    params = section_style()
    params.update(overrides)
    return ft.Container(content=content, **params)


def _action_button(label: str, on_click, *, bgcolor: str | None = None) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        on_click=on_click,
        style=primary_button_style(bgcolor=bgcolor or theme_colors().accent),
    )


def _danger_button(label: str, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        on_click=on_click,
        style=danger_button_style(),
    )


def profile_modal_actions(app, save_label: str, on_save) -> ft.Row:
    return ft.Row(
        [
            ft.TextButton(
                t("common.cancel"),
                on_click=lambda _: app.close_modal(),
                style=on_surface_button_style(),
            ),
            _action_button(save_label, on_save),
        ],
        alignment=ft.MainAxisAlignment.END,
        spacing=12,
    )


RESET_BULLETS_HEIGHT = 220
