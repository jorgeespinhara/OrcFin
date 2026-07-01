"""Tests for roadmap features: seasonal, scenario, recurrence, net worth, MEI tax/receivables."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.db.repositories.categories import (
    create_category,
    get_all_categories,
    get_categories_for_mode,
    is_mei_category,
)
from core.db.repositories.mei import create_mei_invoice, mark_invoice_paid
from core.db.repositories.net_worth import (
    create_asset,
    create_liability,
    get_net_worth_totals,
)
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.db.schema import init_database
from core.services.mei_service import create_mei_profile
from core.models import Transaction, TransactionType, MeiInvoice, Asset, Liability
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights
from core.engine.scenario_simulator import simulate_scenario, ScenarioAdjustment
from core.engine.recurrence_detection import detect_recurring_transactions, get_data_span_days
from core.mei_tax import simulate_me_migration, estimate_mei_annual_tax
from core.mei_receivables import get_receivables_aging
from core.db.connection import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def fresh_db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    yield


def _expense(profile_id: int, cat_id: int, amount: float, d: date, desc: str = "Gasto"):
    create_transaction(
        Transaction(
            profile_id=profile_id,
            category_id=cat_id,
            description=desc,
            amount=Decimal(str(amount)),
            date=d,
            type=TransactionType.EXPENSE,
        )
    )


def test_schema_version_is_current():
    assert SCHEMA_VERSION == 9


def test_mei_categories_hidden_in_personal_mode():
    create_mei_profile("MEI Cat", "Empresa", "11.111.111/0001-11")
    personal = [c for c in get_categories_for_mode(False)]
    mei = [c for c in get_categories_for_mode(True)]
    assert any(is_mei_category(c) for c in get_all_categories())
    assert not any(is_mei_category(c) for c in personal)
    assert all(is_mei_category(c) for c in mei)
    assert any(c.name == "Receita MEI" for c in mei)
    assert not any(c.name == "Receita MEI" for c in personal)


def test_seasonal_comparison_groups_by_month():
    p = create_profile("Seasonal")
    cat = create_category("Comida", TransactionType.EXPENSE)
    _expense(p.id, cat.id, 100, date(2025, 1, 10))
    _expense(p.id, cat.id, 200, date(2026, 1, 10))

    data = get_seasonal_expense_comparison(profile_id=p.id, reference_year=2026, years_back=2)
    jan = next(m for m in data["months"] if m["month"] == 1)
    assert jan["year_totals"][2025] == Decimal("100")
    assert jan["year_totals"][2026] == Decimal("200")
    highlights = get_seasonal_highlights(data)
    assert highlights


def test_scenario_simulator_delta():
    p = create_profile("Sim")
    inc = create_category("Sal", TransactionType.INCOME)
    exp = create_category("Gasto", TransactionType.EXPENSE)
    for m in range(1, 4):
        create_transaction(
            Transaction(
                profile_id=p.id,
                category_id=inc.id,
                description="Salário",
                amount=Decimal("3000"),
                date=date(2026, m, 5),
                type=TransactionType.INCOME,
            )
        )
        _expense(p.id, exp.id, 2000, date(2026, m, 5))

    sim = simulate_scenario(
        profile_id=p.id,
        months_ahead=6,
        adjustments=[ScenarioAdjustment(label="Economia", monthly_expense_delta=Decimal("-500"))],
        end_year=2026,
        end_month=3,
    )
    assert sim["summary"]["scenario_final_cumulative"] > sim["summary"]["base_final_cumulative"]


def test_recurrence_detection_finds_stable_expense():
    p = create_profile("Rec")
    cat = create_category("Assinatura", TransactionType.EXPENSE)
    for m in range(1, 5):
        _expense(p.id, cat.id, 49.90, date(2026, m, 5), desc="Netflix assinatura")

    found = detect_recurring_transactions(profile_id=p.id)
    assert any("netflix" in r["description"].lower() for r in found)
    assert get_data_span_days(profile_id=p.id) >= 0


def test_net_worth_totals():
    p = create_profile("NW")
    create_asset(Asset(profile_id=p.id, name="Conta", asset_type="cash", current_value=Decimal("10000")))
    create_liability(Liability(profile_id=p.id, name="Cartão", liability_type="credit_card", current_balance=Decimal("2000")))
    totals = get_net_worth_totals(p.id)
    assert totals["net_worth"] == Decimal("8000")


def test_mei_receivables_aging_and_payment():
    profile, _ = create_mei_profile("MEI AR", "Empresa", "11.111.111/0001-11")
    today = date.today()
    inv = create_mei_invoice(
        MeiInvoice(
            profile_id=profile.id,
            invoice_number="NF-001",
            tomador_name="Cliente A",
            amount=Decimal("1500"),
            issue_date=today - timedelta(days=40),
            due_date=today - timedelta(days=10),
        )
    )
    aging = get_receivables_aging(profile.id)
    assert aging["outstanding_total"] == Decimal("1500")
    assert len(aging["buckets"]["1_30"]) == 1

    assert mark_invoice_paid(inv.id)
    aging2 = get_receivables_aging(profile.id)
    assert aging2["outstanding_total"] == Decimal("0")


def test_mei_migration_simulator():
    sim = simulate_me_migration(
        ytd_revenue=Decimal("60000"),
        projected_annual=Decimal("95000"),
        activity_type="servico",
    )
    assert sim["exceeds_mei_limit"] is True
    assert sim["recommendation"] == "migrar_obrigatorio"
    assert estimate_mei_annual_tax("servico") > Decimal("0")