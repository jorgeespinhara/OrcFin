"""Dashboard KPI helpers — sparkline, spendable card, action routes."""

from decimal import Decimal

from ui.dashboard.cards import mini_sparkline, build_summary_card, build_spendable_card
from ui.dashboard.sections import _ACTION_ROUTES, _DECISIONS_VISIBLE, run_dashboard_action


def test_mini_sparkline_needs_two_points():
    empty = mini_sparkline([10], "#14B8A6")
    assert empty.width == 0 or empty.height == 0

    spark = mini_sparkline([10, 20, 15, 5], "#14B8A6")
    assert spark.height == 28
    assert spark.width == 88


def test_summary_card_accepts_click_and_sparkline():
    card = build_summary_card(
        "Receitas",
        "R$ 1.000,00",
        "↑ +2%",
        "trending_up",
        "#22C55E",
        on_click=lambda _: None,
        tooltip="Ver lançamentos",
        sparkline_values=[100, 120, 90, 140],
    )
    assert card.on_click is not None
    assert card.ink is True
    assert card.tooltip == "Ver lançamentos"
    assert card.height == 148


def test_spendable_card_bullet_ratio_and_hero_border():
    spend = {
        "income": Decimal("5000"),
        "recurring_fixed": Decimal("1000"),
        "safety_margin": Decimal("500"),
        "spendable": Decimal("2000"),
        "safety_pct": 10.0,
    }
    card = build_spendable_card("R$ 2.000,00", spend, tooltip="Ver orçamentos")
    assert card.tooltip == "Ver orçamentos"
    assert card.height == 148
    # Hero: thicker border than regular KPI cards
    assert card.border is not None


def test_decisions_visible_cap_and_routes():
    assert _DECISIONS_VISIBLE == 5
    assert "transactions" in _ACTION_ROUTES
    assert "budgets" in _ACTION_ROUTES
    assert "reports" in _ACTION_ROUTES
    assert callable(run_dashboard_action)
