"""Central theme palette and control styling for dark/light modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import flet as ft

from core.i18n import t

ThemeModeName = Literal["dark", "light"]


@dataclass(frozen=True)
class AppColors:
    page_bg: str
    surface: str
    surface_alt: str
    border: str
    divider: str
    text_primary: str
    text_secondary: str
    text_muted: str
    field_bg: str
    field_border: str
    nav_bg: str
    nav_bg_mei: str
    appbar_bg: str
    appbar_bg_mei: str
    content_bg: str
    content_bg_mei: str
    modal_bg: str
    modal_border: str
    modal_scrim: str
    snack_error: str
    installment_bg: str
    error_banner_bg: str
    error_banner_border: str
    error_text: str
    mei_banner_bg: str
    mei_banner_text: str
    # Brand / status (same hue in both modes for financial recognition)
    accent: str
    accent_soft: str
    accent_portfolio: str
    accent_card: str
    success: str
    warning: str
    danger: str
    income: str
    expense: str
    on_accent: str


DARK = AppColors(
    page_bg="#0F172A",
    surface="#1E293B",
    surface_alt="#0F172A",
    border="#334155",
    divider="#334155",
    text_primary="#F8FAFC",
    text_secondary="#CBD5E1",
    text_muted="#94A3B8",
    field_bg="#0F172A",
    field_border="#475569",
    nav_bg="#1E293B",
    nav_bg_mei="#292524",
    appbar_bg="#0F172A",
    appbar_bg_mei="#1C1917",
    content_bg="#0F172A",
    content_bg_mei="#0C0A09",
    modal_bg="#1E293B",
    modal_border="#94A3B8",
    modal_scrim="#B3000000",
    snack_error="#EF4444",
    installment_bg="#0F172A",
    error_banner_bg="#450A0A",
    error_banner_border="#EF4444",
    error_text="#FCA5A5",
    mei_banner_bg="#422006",
    mei_banner_text="#FDE68A",
    accent="#14B8A6",
    accent_soft="#0D9488",
    accent_portfolio="#6366F1",
    accent_card="#8B5CF6",
    success="#22C55E",
    warning="#F59E0B",
    danger="#EF4444",
    income="#22C55E",
    expense="#F97316",
    on_accent="#FFFFFF",
)

LIGHT = AppColors(
    page_bg="#F1F5F9",
    surface="#FFFFFF",
    surface_alt="#F8FAFC",
    border="#E2E8F0",
    divider="#CBD5E1",
    text_primary="#0F172A",
    text_secondary="#334155",
    text_muted="#64748B",
    field_bg="#FFFFFF",
    field_border="#CBD5E1",
    nav_bg="#FFFFFF",
    nav_bg_mei="#FFFBEB",
    appbar_bg="#FFFFFF",
    appbar_bg_mei="#FFFBEB",
    content_bg="#F1F5F9",
    content_bg_mei="#F8FAFC",
    modal_bg="#FFFFFF",
    modal_border="#64748B",
    modal_scrim="#66000000",
    snack_error="#DC2626",
    installment_bg="#F8FAFC",
    error_banner_bg="#FEF2F2",
    error_banner_border="#F87171",
    error_text="#B91C1C",
    mei_banner_bg="#FEF3C7",
    mei_banner_text="#92400E",
    accent="#0D9488",
    accent_soft="#14B8A6",
    accent_portfolio="#4F46E5",
    accent_card="#7C3AED",
    success="#16A34A",
    warning="#D97706",
    danger="#DC2626",
    income="#16A34A",
    expense="#EA580C",
    on_accent="#FFFFFF",
)

_active: AppColors = DARK

# Stable brand tokens for modules that import constants (dark-default brand)
PERSONAL_ACCENT = DARK.accent
INCOME_COLOR = DARK.income
EXPENSE_COLOR = DARK.expense
PROJECTION_COLOR = DARK.accent_portfolio
CARD_ACCENT = DARK.accent_card


def set_active(mode: ThemeModeName) -> AppColors:
    global _active
    _active = LIGHT if mode == "light" else DARK
    return _active


def active() -> AppColors:
    return _active


def is_light() -> bool:
    return _active is LIGHT


def field_params(*, accent: str, **overrides) -> dict:
    c = active()
    params = dict(
        color=c.text_primary,
        bgcolor=c.field_bg,
        filled=True,
        fill_color=c.field_bg,
        border_color=c.field_border,
        focused_border_color=accent,
        cursor_color=c.text_primary,
        label_style=ft.TextStyle(color=c.text_secondary, size=13),
        hint_style=ft.TextStyle(color=c.text_muted),
    )
    params.update(overrides)
    return params


def dropdown_params(*, accent: str, **overrides) -> dict:
    c = active()
    params = dict(
        color=c.text_primary,
        filled=True,
        fill_color=c.field_bg,
        border_color=c.field_border,
        focused_border_color=accent,
        label_style=ft.TextStyle(color=c.text_secondary, size=13),
        hint_style=ft.TextStyle(color=c.text_muted),
    )
    params.update(overrides)
    return params


def text_field(*, accent: str, **kwargs) -> ft.TextField:
    return ft.TextField(**field_params(accent=accent, **kwargs))


def dropdown(*, accent: str, **kwargs) -> ft.Dropdown:
    return ft.Dropdown(**dropdown_params(accent=accent, **kwargs))


def title_text(text: str, **kwargs) -> ft.Text:
    c = active()
    size = kwargs.pop("size", 22)
    weight = kwargs.pop("weight", ft.FontWeight.BOLD)
    color = kwargs.pop("color", c.text_primary)
    return ft.Text(text, size=size, weight=weight, color=color, **kwargs)


def body_text(text: str, **kwargs) -> ft.Text:
    c = active()
    color = kwargs.pop("color", c.text_muted)
    size = kwargs.pop("size", 13)
    return ft.Text(text, color=color, size=size, **kwargs)


def caption_text(text: str, **kwargs) -> ft.Text:
    c = active()
    color = kwargs.pop("color", c.text_muted)
    return ft.Text(text, size=12, color=color, **kwargs)


def section_style(*, padding: int = 24, radius: int = 16) -> dict:
    c = active()
    return dict(
        bgcolor=c.surface,
        border_radius=radius,
        padding=padding,
        border=ft.Border.all(1, c.border),
    )


def secondary_text(text: str, **kwargs) -> ft.Text:
    c = active()
    color = kwargs.pop("color", c.text_secondary)
    return ft.Text(text, color=color, **kwargs)


def on_surface_button_style() -> ft.ButtonStyle:
    return ft.ButtonStyle(color=active().text_primary)


def switch_label_style() -> ft.TextStyle:
    return ft.TextStyle(color=active().text_primary)


def primary_button_style(*, bgcolor: str | None = None) -> ft.ButtonStyle:
    c = active()
    return ft.ButtonStyle(
        bgcolor=bgcolor or c.accent,
        color=c.on_accent,
        padding=ft.Padding(left=20, top=12, right=20, bottom=12),
    )


def danger_button_style() -> ft.ButtonStyle:
    c = active()
    return ft.ButtonStyle(bgcolor=c.danger, color=c.on_accent)


def status_color(*, positive: bool | None = None, severity: str | None = None) -> str:
    c = active()
    if severity:
        return {
            "success": c.success,
            "info": c.accent,
            "warning": c.warning,
            "critical": c.danger,
        }.get(severity, c.accent)
    if positive is True:
        return c.success
    if positive is False:
        return c.danger
    return c.text_muted


def format_change(pct: float) -> str:
    if pct > 0:
        return t("theme.change_up", pct=pct)
    if pct < 0:
        return t("theme.change_down", pct=pct)
    return t("theme.change_flat")


def signed_label(value: float | int, *, suffix: str = "%") -> str:
    if value > 0:
        return f"↑ +{value:.1f}{suffix}"
    if value < 0:
        return f"↓ {value:.1f}{suffix}"
    return f"→ 0{suffix}"


def empty_state(
    *,
    icon: str,
    title: str,
    message: str,
    action_label: str | None = None,
    on_action: Callable | None = None,
    accent: str | None = None,
) -> ft.Container:
    c = active()
    color = accent or c.accent
    controls: list[ft.Control] = [
        ft.Icon(icon, size=48, color=color),
        ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=c.text_primary),
        ft.Text(message, size=13, color=c.text_muted, text_align=ft.TextAlign.CENTER),
    ]
    if action_label and on_action:
        controls.append(
            ft.ElevatedButton(
                action_label,
                on_click=lambda e: on_action(e),
                style=primary_button_style(bgcolor=color),
            )
        )
    return ft.Container(
        padding=32,
        content=ft.Column(
            controls,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def collapsible_section(
    title: str,
    content: ft.Control,
    *,
    expanded: bool = False,
    subtitle: str | None = None,
) -> ft.Container:
    """Show/hide block without ExpansionTile (more reliable inside scroll views)."""
    c = active()
    body = ft.Container(content=content, visible=expanded, padding=ft.Padding(0, 8, 0, 0))
    chevron = ft.Icon(
        ft.Icons.EXPAND_LESS if expanded else ft.Icons.EXPAND_MORE,
        color=c.text_muted,
        size=22,
    )

    def toggle(_):
        body.visible = not body.visible
        chevron.name = ft.Icons.EXPAND_LESS if body.visible else ft.Icons.EXPAND_MORE
        if body.page is not None:
            body.update()
            chevron.update()

    header = ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=c.text_primary),
                        ft.Text(subtitle, size=12, color=c.text_muted, visible=bool(subtitle))
                        if subtitle
                        else ft.Container(),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                chevron,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=toggle,
        padding=ft.Padding(4, 4, 4, 4),
        ink=True,
        border_radius=8,
    )
    return ft.Container(
        content=ft.Column([header, body], spacing=0, tight=True),
        border=ft.Border.all(1, c.border),
        border_radius=12,
        bgcolor=c.surface,
        padding=12,
    )


MODAL_BORDER_WIDTH = 2


def modal_dialog_shape(*, radius: int = 16) -> ft.RoundedRectangleBorder:
    c = active()
    return ft.RoundedRectangleBorder(
        radius=radius,
        side=ft.BorderSide(MODAL_BORDER_WIDTH, c.modal_border),
    )


def modal_dialog_kwargs(*, modal: bool = True) -> dict:
    c = active()
    return {
        "bgcolor": c.modal_bg,
        "barrier_color": c.modal_scrim,
        "shape": modal_dialog_shape(),
        "elevation": 16,
        "shadow_color": "#00000066",
        "modal": modal,
    }


def segmented_button_style(*, accent: str) -> ft.ButtonStyle:
    c = active()
    return ft.ButtonStyle(
        side={
            ft.ControlState.DEFAULT: ft.BorderSide(1, c.border),
            ft.ControlState.SELECTED: ft.BorderSide(1, accent),
        },
        bgcolor={
            ft.ControlState.DEFAULT: c.surface,
            ft.ControlState.SELECTED: c.surface_alt,
        },
        color={
            ft.ControlState.DEFAULT: c.text_secondary,
            ft.ControlState.SELECTED: c.text_primary,
        },
    )
