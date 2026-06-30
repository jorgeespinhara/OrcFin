"""Factory reset wipes user data and restores defaults."""

from datetime import date
from decimal import Decimal

import pytest

from core.db.repositories.categories import create_category
from core.db.repositories.credit_cards import create_credit_card, get_credit_cards
from core.db.repositories.profiles import create_profile, get_all_profiles, update_profile
from core.db.repositories.transactions import create_transaction, get_transactions
from core.db.schema import init_database
from core.reset import reset_clean_install, reset_database
from core.models import CreditCard, Transaction, TransactionType
from core.settings_store import (
    load_settings,
    reset_preferences_after_data_wipe,
    save_settings,
    wipe_all_settings,
)


@pytest.fixture(autouse=True)
def fresh_db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "reset.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    yield


def test_reset_all_data_clears_user_records():
    profile = create_profile("Extra")
    cat = create_category("Teste", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date.today(),
            description="Compra",
            amount=Decimal("99"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )
    create_credit_card(
        CreditCard(
            profile_id=profile.id,
            name="Nubank",
            bank="Nubank",
            network="Mastercard",
        )
    )

    reset_database()

    profiles = get_all_profiles()
    assert len(profiles) == 2
    assert {p.name for p in profiles} == {"Usuário 1", "Usuário 2"}
    assert get_transactions() == []
    assert get_credit_cards(profile.id) == []


def test_reset_preferences_after_data_wipe_keeps_ai_settings(project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    save_settings(
        {
            "ai_provider": "grok",
            "ai_api_key": "secret-key",
            "selected_profile_id": 99,
            "app_mode": "mei",
            "filter_year": 2020,
        }
    )

    fresh = reset_preferences_after_data_wipe()

    assert fresh["ai_provider"] == "grok"
    assert fresh["ai_api_key"] == "secret-key"
    assert fresh["selected_profile_id"] is None
    assert fresh["app_mode"] == "personal"
    assert fresh["filter_year"] is None

    reloaded = load_settings()
    assert reloaded["ai_provider"] == "grok"
    assert reloaded["selected_profile_id"] is None


def test_wipe_all_settings_removes_file(project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    save_settings({"ai_provider": "grok", "ai_api_key": "secret-key", "backup_on_close": True})

    fresh = wipe_all_settings()

    assert not cfg.exists()
    assert fresh["ai_provider"] is None
    assert fresh["ai_api_key"] is None
    assert fresh["backup_on_close"] is False


def test_reset_clean_install_wipes_db_and_settings(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "clean.db"
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)

    init_database()
    profile = create_profile("MEI Test")
    save_settings({"ai_provider": "deepseek", "ai_api_key": "key-123", "app_mode": "mei"})

    reset_clean_install()

    assert {p.name for p in get_all_profiles()} == {"Usuário 1", "Usuário 2"}
    assert not cfg.exists()
    assert load_settings()["ai_provider"] is None


def test_clean_install_resets_renamed_profiles(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "renamed.db"
    cfg = project_tmp_path / "settings.json"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)

    init_database()


    profiles = get_all_profiles()
    update_profile(profiles[0].id, "Pam", profiles[0].color)
    update_profile(profiles[1].id, "Jorge", profiles[1].color)
    save_settings({"ai_provider": "grok", "selected_profile_id": profiles[0].id})

    reset_clean_install()

    assert {p.name for p in get_all_profiles()} == {"Usuário 1", "Usuário 2"}


