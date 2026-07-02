"""Onboarding settings and demo seed."""

from core.db.repositories.mei import get_mei_profile
from core.demo_data import seed_demo_mei_data, seed_demo_onboarding, seed_demo_transactions
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


def test_seed_demo_mei_data(fresh_db):
    count, profile_id = seed_demo_mei_data(operational_profile="on_demand")
    assert count >= 4
    assert profile_id is not None
    assert get_mei_profile() is not None


def test_seed_demo_onboarding_mei_mode(fresh_db, project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    settings = dict(load_settings())
    settings["setup_mode"] = "mei"
    settings["mei_operational_profile"] = "recurring"
    personal, mei = seed_demo_onboarding(settings)
    assert personal == 0
    assert mei >= 5
    assert settings.get("mei_profile_id")
    assert get_mei_profile() is not None


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