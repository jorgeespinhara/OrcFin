"""Tests for MEI service functions."""

from datetime import date
from decimal import Decimal

import pytest

from core.db.repositories.mei import get_mei_config
from core.db.schema import init_database
from core.domain.entities.mei_profile import MeiProfile
from core.services.mei_service import confirm_das_payment, create_mei_profile, das_payment_exists


@pytest.fixture(autouse=True)
def fresh_db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    yield


def test_create_mei_profile():
    profile, config = create_mei_profile(
        name="MEI Service",
        razao_social="Empresa LTDA",
        cnpj="12.345.678/0001-99",
        activity_type="comercio",
    )
    assert profile.id is not None
    assert profile.profile_type.value == "mei"
    assert config.razao_social == "Empresa LTDA"

    loaded = get_mei_config(profile.id)
    assert loaded is not None
    entity = MeiProfile(loaded)
    assert entity.das_amount() == Decimal("71.60")


def test_confirm_das_payment():
    profile, config = create_mei_profile("MEI", "Empresa", "11.111.111/0001-11")
    amount = MeiProfile(config).das_amount()

    tx_id = confirm_das_payment(profile.id, date(2026, 6, 20), amount)
    assert tx_id is not None
    assert das_payment_exists(profile.id, 2026, 6)
    assert confirm_das_payment(profile.id, date(2026, 6, 21), amount) is None