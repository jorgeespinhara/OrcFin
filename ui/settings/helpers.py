"""Reusable controls for settings sections."""

import flet as ft

from decimal import Decimal

from core.db.repositories.budgets import delete_budget, get_budgets_for_month, set_budget
from core.db.repositories.categories import (
    create_category,
    delete_category,
    get_categories_for_mode,
)
from core.db.repositories.goals import (
    create_goal,
    delete_goal,
    get_active_goals,
    update_goal_progress,
)
from core.db.repositories.net_worth import (
    create_asset,
    create_liability,
    delete_asset,
    delete_liability,
    get_assets,
    get_liabilities,
    get_net_worth_totals,
)
from core.db.repositories.profiles import (
    create_profile,
    delete_profile,
    get_all_profiles,
    update_profile,
)
from core.models import TransactionType, Asset, Liability
from core.ai_gateway import PROVIDERS
from core.ai_gateway import test_connection as test_provider_connection
from core.engine.categorization import (
    apply_rules_retroactive,
    create_rule,
    delete_rule,
    get_all_rules,
)
from core.backup import (
    create_backup,
    find_latest_backup,
    inspect_backup,
    list_backups,
    prune_backups,
    restore_backup,
)
from core.data_export import export_open_data_json, export_transactions_csv
from core.reset import reset_clean_install, reset_database
from pathlib import Path

from ui.theme import (
    active as theme_colors,
    body_text,
    dropdown_params,
    field_params,
    on_surface_button_style,
    section_style,
    switch_label_style,
    title_text,
)

__all__ = [
    "PROFILE_COLORS",
    "RESET_BULLETS_HEIGHT",
    "_ACCENT",
    "_action_button",
    "_modal_dropdown",
    "_modal_field",
    "_modal_text",
    "body_text",
    "on_surface_button_style",
    "profile_modal_actions",
    "section_card",
    "switch_label_style",
    "theme_colors",
]

PROFILE_COLORS = ["#14B8A6", "#3B82F6", "#8B5CF6", "#F59E0B", "#EF4444", "#EC4899", "#10B981"]
_ACCENT = "#14B8A6"


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


def _action_button(label: str, on_click, *, bgcolor: str = _ACCENT) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        on_click=on_click,
        style=ft.ButtonStyle(bgcolor=bgcolor, color=ft.Colors.WHITE),
    )

def profile_modal_actions(app, save_label: str, on_save) -> ft.Row:
    return ft.Row(
        [
            ft.TextButton(
                "Cancelar",
                on_click=lambda _: app.close_modal(),
                style=on_surface_button_style(),
            ),
            _action_button(save_label, on_save),
        ],
        alignment=ft.MainAxisAlignment.END,
        spacing=12,
    )
RESET_BULLETS_HEIGHT = 220

