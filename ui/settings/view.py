"""Application settings — grouped panels for clearer navigation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import flet as ft

from core.ai_gateway import PROVIDERS
from core.backup_health import assess_backup_health
from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from core.i18n import t
from ui.settings import accounts, appearance, financial, privacy, system
from ui.settings.context import SettingsCtx
from ui.settings.helpers import body_text, theme_colors, title_text
from ui.theme import collapsible_section


@dataclass(frozen=True)
class _SettingsGroup:
    key: str
    label: str
    icon: str
    hint: str
    builder: Callable[[SettingsCtx], ft.Control]


def _panel_column(*sections: ft.Control) -> ft.Column:
    """Stack section cards with consistent gaps; scroll inside the active panel."""
    items: list[ft.Control] = []
    for sec in sections:
        if sec is None:
            continue
        items.append(sec)
        items.append(ft.Container(height=16))
    if items:
        items.pop()
    return ft.Column(
        items,
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        tight=False,
    )


def _build_geral(ctx: SettingsCtx) -> ft.Control:
    return _panel_column(appearance.build_appearance_section(ctx))


def _build_contas(ctx: SettingsCtx) -> ft.Control:
    return _panel_column(
        accounts.build_profiles_section(ctx),
        accounts.build_categories_section(ctx),
    )


def _build_financas(ctx: SettingsCtx) -> ft.Control:
    return _panel_column(
        financial.build_goals_section(ctx),
        financial.build_budgets_section(ctx),
        financial.build_net_worth_section(ctx),
        financial.build_rules_section(ctx),
    )


def _build_dados(ctx: SettingsCtx) -> ft.Control:
    # Stack vertically — more readable than side-by-side in narrow/modal layouts.
    return _panel_column(
        privacy.build_privacy_section(ctx),
        system.build_backup_section(ctx),
        system.build_export_section(ctx),
    )


def _build_ia(ctx: SettingsCtx) -> ft.Control:
    return _panel_column(system.build_ai_section(ctx))


def _build_avancado(ctx: SettingsCtx) -> ft.Control:
    c = theme_colors()
    intro = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    t("settings.danger_title"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=c.danger,
                ),
                body_text(t("settings.danger_body"), size=12),
            ],
            spacing=6,
            tight=True,
        ),
        padding=16,
        bgcolor=c.surface,
        border_radius=12,
        border=ft.Border.all(1, c.danger),
    )
    danger = system.build_danger_zone_section(ctx)
    return _panel_column(
        intro,
        collapsible_section(
            t("settings.danger_zone"),
            danger,
            expanded=False,
            subtitle=t("settings.danger_sub"),
        ),
    )


def _settings_groups() -> list[_SettingsGroup]:
    return [
        _SettingsGroup(
            "geral",
            t("settings.group.geral"),
            ft.Icons.PALETTE_OUTLINED,
            t("settings.hint.geral"),
            _build_geral,
        ),
        _SettingsGroup(
            "contas",
            t("settings.group.contas"),
            ft.Icons.PEOPLE_OUTLINED,
            t("settings.hint.contas"),
            _build_contas,
        ),
        _SettingsGroup(
            "financas",
            t("settings.group.financas"),
            ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
            t("settings.hint.financas"),
            _build_financas,
        ),
        _SettingsGroup(
            "dados",
            t("settings.group.dados"),
            ft.Icons.FOLDER_OUTLINED,
            t("settings.hint.dados"),
            _build_dados,
        ),
        _SettingsGroup(
            "ia",
            t("settings.group.ia"),
            ft.Icons.AUTO_AWESOME_OUTLINED,
            t("settings.hint.ia"),
            _build_ia,
        ),
        _SettingsGroup(
            "avancado",
            t("settings.group.avancado"),
            ft.Icons.WARNING_AMBER_OUTLINED,
            t("settings.hint.avancado"),
            _build_avancado,
        ),
    ]


# Module-level alias kept for tests that import SETTINGS_GROUPS at import time.
SETTINGS_GROUPS = _settings_groups()


def _status_chip(
    label: str,
    value: str,
    *,
    icon: str,
    color: str,
    on_click,
) -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, size=16, color=color),
                ft.Column(
                    [
                        ft.Text(label, size=11, color=c.text_muted),
                        ft.Text(
                            value,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=c.text_primary,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=value,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 8, 12, 8),
        bgcolor=c.surface,
        border=ft.Border.all(1, c.border),
        border_radius=10,
        on_click=on_click,
        ink=True,
        tooltip=t("settings.go_to", label=label),
    )


def _status_row(ctx: SettingsCtx, go_to: Callable[[str], None]) -> ft.Control:
    c = theme_colors()
    settings = ctx.app.settings
    theme_mode = settings.get("theme_mode", "dark")
    theme_label = (
        t("settings.theme_light") if theme_mode == "light" else t("settings.theme_dark")
    )

    health = assess_backup_health(settings)
    level = health.get("level", "")
    backup_color = {
        "otimo": c.success,
        "bom": c.accent,
        "atencao": c.warning,
        "critico": c.danger,
    }.get(level, c.text_muted)
    age = health.get("age_days")
    if age is None:
        backup_value = t("settings.chip_no_backup")
    elif age == 0:
        backup_value = t("settings.backup_today")
    elif age == 1:
        backup_value = t("settings.backup_days_ago_one")
    else:
        backup_value = t("settings.backup_days_ago", days=age)

    keys = dict(settings.get("ai_provider_keys") or {})
    configured = [PROVIDERS[p]["name"] for p in PROVIDERS if keys.get(p)]
    if configured:
        ai_value = (
            configured[0]
            if len(configured) == 1
            else t("settings.ai_providers_n", n=len(configured))
        )
        ai_color = c.success
    else:
        ai_value = t("settings.ai_no_key")
        ai_color = c.text_muted

    n_profiles = len(ctx.profiles) or len(get_all_profiles())
    profiles_value = (
        t("settings.profiles_n", n=n_profiles)
        if n_profiles == 1
        else t("settings.profiles_n_plural", n=n_profiles)
    )

    return ft.Row(
        [
            _status_chip(
                t("settings.chip_theme"),
                theme_label,
                icon=ft.Icons.DARK_MODE if theme_mode != "light" else ft.Icons.LIGHT_MODE,
                color=c.accent,
                on_click=lambda _: go_to("geral"),
            ),
            _status_chip(
                t("settings.chip_backup"),
                backup_value,
                icon=ft.Icons.BACKUP_OUTLINED,
                color=backup_color,
                on_click=lambda _: go_to("dados"),
            ),
            _status_chip(
                t("settings.group.ia"),
                ai_value,
                icon=ft.Icons.AUTO_AWESOME,
                color=ai_color,
                on_click=lambda _: go_to("ia"),
            ),
            _status_chip(
                t("settings.chip_profiles"),
                profiles_value,
                icon=ft.Icons.PEOPLE_OUTLINED,
                color=c.accent_portfolio,
                on_click=lambda _: go_to("contas"),
            ),
        ],
        spacing=10,
        wrap=True,
    )


def _nav_button(
    group: _SettingsGroup,
    *,
    selected: bool,
    on_click,
) -> ft.Container:
    c = theme_colors()
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    group.icon,
                    size=20,
                    color=c.accent if selected else c.text_muted,
                ),
                ft.Column(
                    [
                        ft.Text(
                            group.label,
                            size=13,
                            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                            color=c.text_primary if selected else c.text_secondary,
                        ),
                        ft.Text(
                            group.hint,
                            size=11,
                            color=c.text_muted,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 10, 12, 10),
        bgcolor=c.surface_alt if selected else None,
        border=ft.Border.all(1, c.accent if selected else c.border),
        border_radius=10,
        on_click=on_click,
        ink=True,
        margin=ft.Margin.only(bottom=6),
    )


class SettingsView:
    def __init__(self, app: "OrcFinApp", *, initial_group: str | None = None):
        self.ctx = SettingsCtx(
            app=app,
            profiles=get_all_profiles(),
            categories=get_categories_for_mode(app.is_mei_mode()),
        )
        keys = {g.key for g in SETTINGS_GROUPS}
        self._group_key = initial_group if initial_group in keys else "geral"

    def build(self) -> ft.Control:
        ctx = self.ctx
        c = theme_colors()
        panel_host = ft.Container(expand=True)
        nav_host = ft.Column(spacing=0, tight=True)
        group_title = ft.Text("", size=18, weight=ft.FontWeight.W_600, color=c.text_primary)
        group_hint = ft.Text("", size=12, color=c.text_muted)

        def current_group() -> _SettingsGroup:
            for g in SETTINGS_GROUPS:
                if g.key == self._group_key:
                    return g
            return SETTINGS_GROUPS[0]

        def render_panel():
            group = current_group()
            group_title.value = group.label
            group_hint.value = group.hint
            panel_host.content = group.builder(ctx)
            nav_host.controls = [
                _nav_button(
                    g,
                    selected=g.key == self._group_key,
                    on_click=lambda _, key=g.key: select_group(key),
                )
                for g in SETTINGS_GROUPS
            ]

        def select_group(key: str):
            if key == self._group_key and panel_host.content is not None:
                # Still refresh nav selection styling when coming from chips of same group
                pass
            self._group_key = key
            render_panel()
            if panel_host.page is not None:
                panel_host.update()
                nav_host.update()
                group_title.update()
                group_hint.update()

        def go_to(key: str):
            select_group(key)

        render_panel()

        header = ft.Column(
            [
                title_text(t("settings.title")),
                body_text(t("settings.subtitle"), size=13),
                ft.Container(height=8),
                _status_row(ctx, go_to),
            ],
            spacing=4,
            tight=True,
        )

        sidebar = ft.Container(
            content=ft.Column(
                [
                    ft.Text(t("settings.areas"), size=12, weight=ft.FontWeight.W_600, color=c.text_muted),
                    nav_host,
                ],
                spacing=8,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=200,
            padding=ft.Padding.only(right=8),
        )

        content = ft.Container(
            content=ft.Column(
                [
                    group_title,
                    group_hint,
                    ft.Container(height=12),
                    panel_host,
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            padding=ft.Padding.only(left=8),
        )

        return ft.Container(
            expand=True,
            content=ft.Column(
                [
                    header,
                    ft.Container(height=16),
                    ft.Row(
                        [
                            sidebar,
                            ft.VerticalDivider(width=1, color=c.divider),
                            content,
                        ],
                        expand=True,
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        )
