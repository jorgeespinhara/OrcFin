"""Theme and display preferences."""

from __future__ import annotations

import flet as ft

from core.i18n import COUNTRY_PRESETS, SUPPORTED_LOCALES, apply_from_settings, t
from core.settings_store import save_settings
from ui.mei.constants import PERSONAL_ACCENT
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *
from ui.theme import segmented_button_style


_LOCALE_LABELS = {
    "pt-BR": "Português (Brasil)",
    "en-US": "English (US)",
    "es-ES": "Español (España)",
}


def build_appearance_section(ctx: SettingsCtx) -> ft.Container:
    current = ctx.app.settings.get("theme_mode", "dark")
    if current not in ("dark", "light"):
        current = "dark"

    theme_toggle = ft.SegmentedButton(
        selected=[current],
        on_change=lambda e: on_theme_mode_change(ctx, e),
        style=segmented_button_style(accent=PERSONAL_ACCENT),
        segments=[
            ft.Segment(value="dark", label=ft.Text(t("settings.theme_dark")), icon=ft.Icons.DARK_MODE),
            ft.Segment(value="light", label=ft.Text(t("settings.theme_light")), icon=ft.Icons.LIGHT_MODE),
        ],
    )

    locale_value = ctx.app.settings.get("locale") or "pt-BR"
    if locale_value not in SUPPORTED_LOCALES:
        locale_value = "pt-BR"
    country_value = (ctx.app.settings.get("country_profile") or "BR").upper()
    if country_value not in COUNTRY_PRESETS:
        country_value = "BR"

    locale_dd = ft.Dropdown(
        label=t("settings.language_label"),
        value=locale_value,
        width=260,
        options=[ft.dropdown.Option(code, _LOCALE_LABELS.get(code, code)) for code in SUPPORTED_LOCALES],
        on_select=lambda e: _on_locale_change(ctx, e),
    )
    country_dd = ft.Dropdown(
        label=t("settings.country_label"),
        value=country_value,
        width=260,
        options=[
            ft.dropdown.Option(
                code,
                f"{preset['flag']} {t(preset['name_key'])}",
            )
            for code, preset in COUNTRY_PRESETS.items()
        ],
        on_select=lambda e: _on_country_change(ctx, e),
    )

    return section_card(
        ft.Column(
            [
                _modal_text(t("settings.appearance_title"), size=16, weight=ft.FontWeight.W_600),
                body_text(t("settings.appearance_body"), size=12),
                ft.Row([theme_toggle], alignment=ft.MainAxisAlignment.START),
                _modal_text(t("settings.language_title"), size=16, weight=ft.FontWeight.W_600),
                body_text(t("settings.language_body"), size=12),
                ft.Row([locale_dd, country_dd], spacing=12, wrap=True),
            ],
            spacing=10,
        ),
    )


def on_theme_mode_change(ctx: SettingsCtx, e: ft.ControlEvent):
    selected = next(iter(e.control.selected), "dark")
    ctx.app.apply_theme_mode(selected)


def _on_locale_change(ctx: SettingsCtx, e: ft.ControlEvent):
    locale = e.control.value or "pt-BR"
    ctx.app.settings["locale"] = locale
    apply_from_settings(ctx.app.settings)
    save_settings(ctx.app.settings)
    if hasattr(ctx.app, "refresh_current_view"):
        ctx.app.refresh_current_view()
    if hasattr(ctx.app, "show_snack"):
        ctx.app.show_snack(t("settings.language_saved"))


def _on_country_change(ctx: SettingsCtx, e: ft.ControlEvent):
    code = (e.control.value or "BR").upper()
    preset = COUNTRY_PRESETS.get(code) or COUNTRY_PRESETS["BR"]
    ctx.app.settings["country_profile"] = code
    # Keep user's UI language; only sync currency (and force out of MEI if needed).
    ctx.app.settings["currency"] = preset["currency"]
    if not preset["mei"]:
        ctx.app.settings["app_mode"] = "personal"
        if hasattr(ctx.app, "state"):
            ctx.app.state.app_mode = "personal"
    apply_from_settings(ctx.app.settings)
    save_settings(ctx.app.settings)
    if hasattr(ctx.app, "_sync_shell_chrome"):
        ctx.app._sync_shell_chrome()
    if hasattr(ctx.app, "nav_rail") and hasattr(ctx.app, "enter_personal_shell"):
        # Rebuild nav labels / hide MEI chrome without full restart.
        from ui.router import personal_destinations

        if not preset["mei"] and getattr(ctx.app, "is_mei_mode", lambda: False)():
            ctx.app.enter_personal_shell()
        else:
            ctx.app.nav_rail.destinations = personal_destinations()
            if hasattr(ctx.app, "refresh_current_view"):
                ctx.app.refresh_current_view()
    elif hasattr(ctx.app, "refresh_current_view"):
        ctx.app.refresh_current_view()
    if hasattr(ctx.app, "show_snack"):
        ctx.app.show_snack(t("settings.language_saved"))
