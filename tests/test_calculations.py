"""Tests for core financial calculations."""

from datetime import date
from decimal import Decimal

import pytest

from core.engine.reporting import (
    _safe_pct_change,
    get_year_to_date_summary,
    get_balance_evolution_anchored,
    get_monthly_income_expense_series,
    build_projection_chart_points,
    build_forward_projection,
    calculate_simple_projection,
    get_dashboard_data,
    get_top_expense_categories_with_trend,
)
from core.db.queries import (
    get_category_breakdown_with_projections,
    get_monthly_summary,
    get_ytd_totals,
)
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.db.schema import init_database
from core.models import Transaction, TransactionType


@pytest.fixture(autouse=True)
def fresh_db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    if db_path.exists():
        db_path.unlink()
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()
    yield


def _seed_tx(profile_id: int, category_id: int, amount: float, month: int, tx_type: TransactionType):
    create_transaction(
        Transaction(
            profile_id=profile_id,
            category_id=category_id,
            description="Test",
            amount=Decimal(str(amount)),
            date=date(2026, month, 15),
            type=tx_type,
        )
    )


def test_safe_pct_change():
    assert _safe_pct_change(Decimal("100"), Decimal("150")) == pytest.approx(50.0)
    assert _safe_pct_change(Decimal("0"), Decimal("0")) == 0.0
    assert _safe_pct_change(Decimal("0"), Decimal("50")) == 100.0


def test_ytd_single_query_matches_monthly_loop():
    p = create_profile("Test")
    c_income = create_category("Sal", TransactionType.INCOME)
    c_expense = create_category("Gasto", TransactionType.EXPENSE)
    _seed_tx(p.id, c_income.id, 1000, 1, TransactionType.INCOME)
    _seed_tx(p.id, c_expense.id, 400, 1, TransactionType.EXPENSE)
    _seed_tx(p.id, c_income.id, 2000, 2, TransactionType.INCOME)
    _seed_tx(p.id, c_expense.id, 500, 2, TransactionType.EXPENSE)

    ytd = get_ytd_totals(year=2026, up_to_month=2, profile_id=p.id, consolidated=False)
    m1 = get_monthly_summary(2026, 1, p.id)
    m2 = get_monthly_summary(2026, 2, p.id)

    assert ytd["total_income"] == m1["total_income"] + m2["total_income"]
    assert ytd["total_expense"] == m1["total_expense"] + m2["total_expense"]
    assert ytd["net_savings"] == ytd["total_income"] - ytd["total_expense"]


def test_get_year_to_date_summary_wrapper():
    p = create_profile("YTD User")
    cat = create_category("Renda", TransactionType.INCOME)
    _seed_tx(p.id, cat.id, 500, 1, TransactionType.INCOME)

    summary = get_year_to_date_summary(profile_id=p.id, consolidated=False, year=2026, up_to_month=1)
    assert summary["total_income"] == Decimal("500")
    assert summary["year"] == 2026


def test_balance_evolution_anchored():
    p = create_profile("Evo User")
    c_income = create_category("Sal Evo", TransactionType.INCOME)
    _seed_tx(p.id, c_income.id, 100, 1, TransactionType.INCOME)
    _seed_tx(p.id, c_income.id, 200, 2, TransactionType.INCOME)
    _seed_tx(p.id, c_income.id, 300, 3, TransactionType.INCOME)

    evolution = get_balance_evolution_anchored(
        months_back=3,
        end_year=2026,
        end_month=3,
        profile_id=p.id,
    )
    assert len(evolution) == 3
    assert evolution[-1]["cumulative_balance"] == Decimal("600")


def test_projection_forward_total_excludes_prior_cumulative():
    evolution = [
        {
            "year": 2026,
            "month": 6,
            "label": "06/2026",
            "net_savings": Decimal("-2287"),
            "cumulative_balance": Decimal("-2287"),
            "income": Decimal("0"),
            "expense": Decimal("2287"),
        },
        {
            "year": 2026,
            "month": 7,
            "label": "07/2026",
            "net_savings": Decimal("-2287"),
            "cumulative_balance": Decimal("-4574"),
            "income": Decimal("0"),
            "expense": Decimal("2287"),
        },
    ]
    projection = calculate_simple_projection(evolution, months_ahead=3)
    assert projection["projected_in_3_months"] == Decimal("-6861")
    assert projection["projected_cumulative_at_horizon"] == Decimal("-11435")


def test_projection_chart_points():
    evolution = [
        {"year": 2026, "month": 1, "label": "01/2026", "net_savings": Decimal("100"), "cumulative_balance": Decimal("100")},
        {"year": 2026, "month": 2, "label": "02/2026", "net_savings": Decimal("100"), "cumulative_balance": Decimal("200")},
    ]
    points = build_projection_chart_points(evolution, months_ahead=2)
    assert len(points) == 2
    assert points[0]["is_projected"] is True
    assert points[1]["projected_cumulative"] == Decimal("400")


def test_build_forward_projection_breaks_down_income_and_expense():
    p = create_profile("Forecast User")
    c_income = create_category("Salário Forecast", TransactionType.INCOME)
    c_expense = create_category("Moradia Forecast", TransactionType.EXPENSE)
    _seed_tx(p.id, c_income.id, 5000, 6, TransactionType.INCOME)
    _seed_tx(p.id, c_expense.id, 2000, 6, TransactionType.EXPENSE)

    forecast = build_forward_projection(
        profile_id=p.id,
        consolidated=False,
        end_year=2026,
        end_month=6,
        months_ahead=3,
    )

    assert forecast["projected_income_total"] == Decimal("15000")
    assert forecast["projected_expense_total"] == Decimal("6000")
    assert forecast["projected_net_total"] == Decimal("9000")
    assert len(forecast["monthly_points"]) == 3
    assert forecast["has_history"] is True


def test_top_expense_categories_with_trend():
    p = create_profile("Trend User")
    c_a = create_category("Mercado", TransactionType.EXPENSE)
    c_b = create_category("Transporte", TransactionType.EXPENSE)
    _seed_tx(p.id, c_a.id, 300, 5, TransactionType.EXPENSE)
    _seed_tx(p.id, c_a.id, 500, 6, TransactionType.EXPENSE)
    _seed_tx(p.id, c_b.id, 100, 6, TransactionType.EXPENSE)

    ranked = get_top_expense_categories_with_trend(
        profile_id=p.id,
        consolidated=False,
        end_year=2026,
        end_month=6,
        months_back=3,
        limit=4,
    )
    assert len(ranked) == 2
    assert ranked[0]["name"] == "Mercado"
    assert ranked[0]["total"] == Decimal("800")


def test_future_month_projects_recurring_categories():
    p = create_profile("Recurring User")
    c_school = create_category("Escola", TransactionType.EXPENSE)
    c_club = create_category("Clube", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=c_school.id,
            description="Mensalidade escola",
            amount=Decimal("1500"),
            date=date(2026, 6, 10),
            type=TransactionType.EXPENSE,
            is_recurring=True,
        )
    )
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=c_club.id,
            description="Clube",
            amount=Decimal("600"),
            date=date(2026, 6, 12),
            type=TransactionType.EXPENSE,
            is_recurring=True,
        )
    )

    breakdown, projected = get_category_breakdown_with_projections(
        2026, 7, profile_id=p.id, type_filter=TransactionType.EXPENSE
    )
    assert projected is True
    assert len(breakdown) == 2
    assert sum(item["total"] for item in breakdown) == Decimal("2100")

    dash = get_dashboard_data(profile_id=p.id, consolidated=False, year=2026, month=7)
    assert dash["category_breakdown_is_projected"] is True
    assert dash["current_month"]["total_expense"] == Decimal("2100")


def test_dashboard_data_with_period_filter():
    p = create_profile("Dash User")
    c_income = create_category("Sal Dash", TransactionType.INCOME)
    c_expense = create_category("Gasto Dash", TransactionType.EXPENSE)
    _seed_tx(p.id, c_income.id, 3000, 6, TransactionType.INCOME)
    _seed_tx(p.id, c_expense.id, 1000, 6, TransactionType.EXPENSE)

    dash = get_dashboard_data(profile_id=p.id, consolidated=False, year=2026, month=6)
    assert dash["current_month"]["total_income"] == Decimal("3000")
    assert dash["current_month"]["total_expense"] == Decimal("1000")
    assert len(dash["monthly_series"]) == 12
    assert dash["projection_chart"]


def test_monthly_income_expense_series():
    p = create_profile("Series User")
    c_income = create_category("Sal Series", TransactionType.INCOME)
    _seed_tx(p.id, c_income.id, 500, 5, TransactionType.INCOME)

    series = get_monthly_income_expense_series(
        months_back=2,
        end_year=2026,
        end_month=5,
        profile_id=p.id,
    )
    assert len(series) == 2
    assert series[-1]["income"] == Decimal("500")


def test_settings_encryption_roundtrip(project_tmp_path, monkeypatch):
    import json

    import core.settings_store as store
    from core.settings_store import load_settings, save_settings

    test_file = project_tmp_path / "settings.json"
    monkeypatch.setattr(store, "CONFIG_FILE", test_file)

    save_settings({"ai_api_key": "sk-test-secret", "theme_mode": "dark"})
    raw = json.loads(test_file.read_text(encoding="utf-8"))
    assert "sk-test-secret" not in test_file.read_text(encoding="utf-8")
    assert str(raw["ai_api_key"]).startswith("enc:v1:")
    loaded = load_settings()
    assert loaded["ai_api_key"] == "sk-test-secret"
