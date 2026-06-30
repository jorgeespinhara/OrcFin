"""Tests for domain layer."""

from decimal import Decimal

from core.domain.entities.mei_profile import DAS_AMOUNTS, MeiProfile
from core.domain.value_objects.money import format_brl
from core.models import MeiConfig


def test_format_brl_positive():
    assert format_brl(Decimal("1234.56")) == "R$ 1.234,56"


def test_format_brl_negative():
    assert format_brl(Decimal("-50.5")) == "-R$ 50,50"


def test_mei_profile_das_amount():
    config = MeiConfig(
        profile_id=1,
        razao_social="Test",
        cnpj="00.000.000/0001-00",
        activity_type="servico",
    )
    assert MeiProfile(config).das_amount() == DAS_AMOUNTS["servico"]


def test_mei_profile_custom_das():
    config = MeiConfig(
        profile_id=1,
        razao_social="Test",
        cnpj="00.000.000/0001-00",
        custom_das_amount=99.0,
    )
    assert MeiProfile(config).das_amount() == Decimal("99")


def test_mei_profile_revenue_limit_status():
    config = MeiConfig(
        profile_id=1,
        razao_social="Test",
        cnpj="00.000.000/0001-00",
        annual_limit=81000.0,
    )
    status = MeiProfile(config).revenue_limit_status(Decimal("70000"))
    assert status["at_risk"] is True
    assert status["exceeded"] is False


def test_mei_profile_das_due_info():
    from datetime import date

    config = MeiConfig(
        profile_id=1,
        razao_social="Test",
        cnpj="00.000.000/0001-00",
        activity_type="servico",
    )
    info = MeiProfile(config).das_due_info(date(2026, 6, 15))
    assert info["due_date"].day == 20
    assert info["days_left"] == 5