"""Onboarding settings and demo seed."""

from core.db.queries import get_category_breakdown
from core.db.repositories.goals import get_active_goals
from core.db.repositories.mei import get_mei_profile
from core.db.repositories.transactions import get_transactions
from core.demo_data import seed_demo_mei_data, seed_demo_onboarding, seed_demo_transactions
from core.i18n import apply_locale_settings, clear_locale_cache, t
from core.models import TransactionType
from core.settings_store import DEFAULT_SETTINGS, load_settings, save_settings


def test_default_settings_include_onboarding(fresh_db, project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    settings = load_settings()
    assert settings["onboarding_completed"] is False
    assert settings["setup_mode"] == "personal"
    assert settings["locale"] == "pt-BR"
    assert settings["country_profile"] == "BR"


def test_seed_demo_transactions(fresh_db):
    count = seed_demo_transactions()
    assert count >= 80


def test_seed_demo_transactions_localized_en(fresh_db):
    clear_locale_cache()
    apply_locale_settings(locale="en-US", country_profile="US", currency="USD")
    count = seed_demo_transactions()
    assert count >= 80

    goals = get_active_goals()
    goal_names = {g["name"] for g in goals}
    assert t("demo.goal.emergency") in goal_names
    assert t("demo.goal.travel") in goal_names
    assert "Reserva de emergência demo" not in goal_names

    txs = get_transactions(limit=50)
    descriptions = {tx.description for tx in txs}
    assert t("demo.tx.salary") in descriptions
    assert "Salário demo" not in descriptions

    from datetime import date

    today = date.today()
    breakdown = get_category_breakdown(today.year, today.month, type_filter=TransactionType.EXPENSE)
    names = {row["name"] for row in breakdown}
    # system categories must show English labels, not Portuguese seed names
    assert any("Housing" in n or "Food" in n or "Transport" in n for n in names)
    assert not any("Moradia" in n or "Alimentação" in n for n in names)


def test_seed_demo_mei_data(fresh_db):
    count, profile_id = seed_demo_mei_data(operational_profile="on_demand")
    assert count >= 50
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
    assert mei >= 50
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