"""Shared UI for MEI operational profile selection."""

from __future__ import annotations

import flet as ft

from core.i18n import t
from core.mei_operational import (
    DEFAULT_PROFILE,
    PROFILES,
    suggest_profile,
)
from ui.mei.components import mei_text


def _profile_label(key: str) -> str:
    return t(f"mei.profile.{key}")


def _profile_hint(key: str) -> str:
    return t(f"mei.profile_hint.{key}")


def profile_dropdown(*, value: str | None, width: int = 400) -> ft.Dropdown:
    return ft.Dropdown(
        label=t("mei.profile.label"),
        value=value or DEFAULT_PROFILE,
        width=width,
        options=[ft.dropdown.Option(key, _profile_label(key)) for key in PROFILES],
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
                label=f"{_profile_label(key)} · {_profile_hint(key)}",
            )
        )
    return ft.RadioGroup(
        value=value or DEFAULT_PROFILE,
        content=ft.Column(options, spacing=4, tight=True),
        on_change=on_change,
    )


def cnae_field(*, value: str = "", on_change=None, width: int = 400) -> ft.TextField:
    return ft.TextField(
        label=t("mei.profile.cnae"),
        hint_text=t("mei.profile.cnae_hint"),
        value=value,
        width=width,
        max_length=9,
        on_change=on_change,
    )


def profile_hint_text(profile: str | None) -> ft.Text:
    key = profile if profile in PROFILES else DEFAULT_PROFILE
    return mei_text(_profile_hint(key), size=12, muted=True)


def suggest_from_cnae(cnae: str) -> str:
    return suggest_profile(cnae)
