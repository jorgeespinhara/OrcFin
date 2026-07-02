"""Theme and display preferences."""

from __future__ import annotations

import flet as ft

from ui.mei.constants import PERSONAL_ACCENT
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *
from ui.theme import segmented_button_style


def build_appearance_section(ctx: SettingsCtx) -> ft.Container:
    current = ctx.app.settings.get("theme_mode", "dark")
    if current not in ("dark", "light"):
        current = "dark"

    theme_toggle = ft.SegmentedButton(
        selected=[current],
        on_change=lambda e: on_theme_mode_change(ctx, e),
        style=segmented_button_style(accent=PERSONAL_ACCENT),
        segments=[
            ft.Segment(value="dark", label=ft.Text("Escuro"), icon=ft.Icons.DARK_MODE),
            ft.Segment(value="light", label=ft.Text("Claro"), icon=ft.Icons.LIGHT_MODE),
        ],
    )

    return section_card(
        ft.Column(
            [
                _modal_text("Aparência", size=16, weight=ft.FontWeight.W_600),
                body_text(
                    "Escolha o tema da interface. O modo claro usa fundos claros e texto escuro para leitura confortável.",
                    size=11,
                ),
                ft.Row(
                    [
                        theme_toggle,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            spacing=10,
        ),
    )

def on_theme_mode_change(ctx: SettingsCtx, e: ft.ControlEvent):
    selected = next(iter(e.control.selected), "dark")
    ctx.app.apply_theme_mode(selected)
