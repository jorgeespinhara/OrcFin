"""Smoke test — settings package imports after split."""

from ui.settings import SettingsView
from ui.settings.context import SettingsCtx
from ui.settings import appearance, accounts, financial, system


def test_settings_submodules_expose_builders():
    assert callable(appearance.build_appearance_section)
    assert callable(accounts.build_profiles_section)
    assert callable(financial.build_goals_section)
    assert callable(system.build_backup_section)


def test_settings_view_class():
    assert SettingsView.__name__ == "SettingsView"