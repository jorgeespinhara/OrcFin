"""Smoke imports after UI package split."""

from ui.personal.charts import PERSONAL_ACCENT, projection_forecast_chart
from ui.transactions import TransactionsView
from ui.dashboard import DashboardView
from ui.reports import ReportsView


def test_ui_packages_import():
    assert PERSONAL_ACCENT == "#14B8A6"
    assert callable(projection_forecast_chart)
    for cls in (TransactionsView, DashboardView, ReportsView):
        assert hasattr(cls, "build")