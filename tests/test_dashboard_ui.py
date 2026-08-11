"""Dashboard KPI helpers — sparkline, spendable card, action routes."""

from decimal import Decimal

from ui.dashboard.cards import mini_sparkline, build_summary_card, build_spendable_card
from ui.dashboard.sections import _ACTION_ROUTES, _DECISIONS_VISIBLE, run_dashboard_action
from ui.personal.charts.bars import category_breakdown_chart


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


def test_category_breakdown_hero_others_and_pct():
    from core.i18n import apply_locale_settings, clear_locale_cache, t
    from ui.personal.charts.bars import category_share_items

    clear_locale_cache()
    apply_locale_settings(locale="en-US")
    cats = [
        {"name": f"Cat {i}", "icon": "📦", "total": Decimal(100 - i * 5)}
        for i in range(8)
    ]
    items, total = category_share_items(cats, max_items=3)
    assert total == sum(float(c["total"]) for c in cats)
    assert abs(sum(i["value"] for i in items) - total) < 0.01
    assert any(t("dash.chart_others") in i["label"] for i in items)

    chart = category_breakdown_chart(cats, max_items=3, expense_change_pct=12.5)
    # header + bars + comparison footer
    assert chart is not None
    assert len(chart.controls) == 3


def test_income_expense_chart_builds_with_comparison():
    from ui.personal.charts.bars import income_expense_chart

    series = [
        {"year": 2025, "month": m, "income": 1000 + m * 10, "expense": 800 + m * 5, "net_savings": 200}
        for m in range(1, 13)
    ]
    chart = income_expense_chart(
        series,
        compact=True,
        max_months=12,
        expense_change_pct=-5.0,
        income_change_pct=3.0,
    )
    assert chart is not None
    assert len(chart.controls) >= 13  # header + 12 months + footer


def test_bill_urgency_buckets():
    from datetime import date, timedelta
    from core.engine.due_dates import bill_urgency

    today = date(2026, 6, 15)
    assert bill_urgency(today - timedelta(days=1), today) == "overdue"
    assert bill_urgency(today, today) == "soon"
    assert bill_urgency(today + timedelta(days=2), today) == "soon"
    assert bill_urgency(today + timedelta(days=5), today) == "week"
    assert bill_urgency(today + timedelta(days=20), today) == "later"


def test_net_worth_strip_builds():
    from ui.dashboard.cards import build_net_worth_strip

    strip = build_net_worth_strip(
        net_worth="R$ 10.000,00",
        assets="R$ 12.000,00",
        liabilities="R$ 2.000,00",
        sparkline_values=[8_000, 9_000, 10_000],
        tooltip="tip",
    )
    assert strip.tooltip == "tip"
    assert strip.on_click is None


def test_decisions_visible_cap_and_routes():
    assert _DECISIONS_VISIBLE == 5
    assert "transactions" in _ACTION_ROUTES
    assert "budgets" in _ACTION_ROUTES
    assert "reports" in _ACTION_ROUTES
    assert callable(run_dashboard_action)
