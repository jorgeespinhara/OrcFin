"""Onboarding settings and demo seed."""

from core.demo_data import seed_demo_transactions
from core.settings_store import DEFAULT_SETTINGS, load_settings, save_settings


def test_default_settings_include_onboarding(fresh_db, project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    settings = load_settings()
    assert settings["onboarding_completed"] is False
    assert settings["setup_mode"] == "personal"


def test_seed_demo_transactions(fresh_db):
    count = seed_demo_transactions()
    assert count >= 3


def test_onboarding_flag_persists(fresh_db, project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    settings = dict(DEFAULT_SETTINGS)
    settings["onboarding_completed"] = True
    settings["setup_mode"] = "both"
    save_settings(settings)
    loaded = load_settings()
    assert loaded["onboarding_completed"] is True
    assert loaded["setup_mode"] == "both"