"""Tests for credit card import helper."""

from core.db.repositories.credit_cards import get_credit_cards
from core.db.schema import init_database
from core.services.credit_card_service import get_or_create_credit_card_from_import


def test_get_or_create_from_import_creates_then_reuses(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()

    from core.db.repositories.profiles import create_profile

    profile = create_profile("Personal", "#14B8A6")

    first = get_or_create_credit_card_from_import(
        profile.id,
        bank="Nubank",
        network="Mastercard",
        last_four="1234",
        due_day=10,
    )
    assert first.id is not None
    assert "Nubank" in first.name
    assert first.last_four == "1234"

    second = get_or_create_credit_card_from_import(
        profile.id,
        bank="Nubank",
        network="Mastercard",
        last_four="1234",
    )
    assert second.id == first.id
    assert len(get_credit_cards(profile.id)) == 1