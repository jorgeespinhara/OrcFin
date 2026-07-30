"""Smoke test — settings package imports after split."""

from ui.settings import SettingsView
from ui.settings.context import SettingsCtx
from ui.settings import appearance, accounts, financial, system
from ui.settings.view import SETTINGS_GROUPS


class _StubApp:
    settings = {
        "theme_mode": "dark",
        "backup_on_close": False,
        "backup_interval_days": 7,
        "backup_retention_count": 5,
        "ai_provider_keys": {},
    }
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


def test_settings_groups_cover_main_areas():
    keys = {g.key for g in SETTINGS_GROUPS}
    assert keys == {"geral", "contas", "financas", "dados", "ia", "avancado"}


def test_settings_view_builds(fresh_db):
    view = SettingsView(_StubApp())
    root = view.build()
    assert root is not None
    # Each group builder returns a control without raising.
    ctx = view.ctx
    for group in SETTINGS_GROUPS:
        panel = group.builder(ctx)
        assert panel is not None


def test_settings_helpers_star_import(fresh_db):
    ctx = _ctx()
    appearance.build_appearance_section(ctx)
    accounts.build_profiles_section(ctx)
    financial.build_goals_section(ctx)
    system.build_backup_section(ctx)