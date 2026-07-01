"""Smoke test — settings package imports after split."""

from ui.settings import SettingsView
from ui.settings.context import SettingsCtx
from ui.settings import appearance, accounts, financial, system


class _StubApp:
    settings = {"theme_mode": "dark", "backup_on_close": False, "backup_interval_days": 7, "backup_retention_count": 5}
    filter_year = None
    filter_month = None
    is_consolidated = False

    def get_view_profile_id(self):
        return None

    def is_mei_mode(self):
        return False

    def _save_settings(self):
        pass

    def apply_theme_mode(self, _mode):
        pass


def _ctx():
    return SettingsCtx(app=_StubApp(), profiles=[], categories=[])


def test_settings_submodules_expose_builders():
    assert callable(appearance.build_appearance_section)
    assert callable(accounts.build_profiles_section)
    assert callable(financial.build_goals_section)
    assert callable(system.build_backup_section)


def test_settings_view_class():
    assert SettingsView.__name__ == "SettingsView"


def test_settings_helpers_star_import(fresh_db):
    ctx = _ctx()
    appearance.build_appearance_section(ctx)
    accounts.build_profiles_section(ctx)
    financial.build_goals_section(ctx)
    system.build_backup_section(ctx)