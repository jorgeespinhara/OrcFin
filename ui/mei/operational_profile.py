"""Shared UI for MEI operational profile selection."""

from __future__ import annotations

import flet as ft

from core.mei_operational import (
    DEFAULT_PROFILE,
    PROFILE_HINTS,
    PROFILE_LABELS,
    PROFILES,
    suggest_profile,
)
from ui.mei.components import mei_text


def profile_dropdown(*, value: str | None, width: int = 400) -> ft.Dropdown:
    return ft.Dropdown(
        label="Perfil operacional",
        value=value or DEFAULT_PROFILE,
        width=width,
        options=[ft.dropdown.Option(key, PROFILE_LABELS[key]) for key in PROFILES],
    )


def profile_radio_group(
    *,
    value: str | None,
    on_change,
) -> ft.RadioGroup:
    options = []
    for key in PROFILES:
        options.append(
            ft.Radio(
                value=key,
                label=f"{PROFILE_LABELS[key]} · {PROFILE_HINTS[key]}",
            )
        )
    return ft.RadioGroup(
        value=value or DEFAULT_PROFILE,
        content=ft.Column(options, spacing=4, tight=True),
        on_change=on_change,
    )


def cnae_field(*, value: str = "", on_change=None, width: int = 400) -> ft.TextField:
    return ft.TextField(
        label="CNAE principal (opcional)",
        hint_text="Ex.: 1412602",
        value=value,
        width=width,
        max_length=9,
        on_change=on_change,
    )


def profile_hint_text(profile: str | None) -> ft.Text:
    key = profile if profile in PROFILE_LABELS else DEFAULT_PROFILE
    return mei_text(PROFILE_HINTS[key], size=12, muted=True)


def suggest_from_cnae(cnae: str) -> str:
    return suggest_profile(cnae)