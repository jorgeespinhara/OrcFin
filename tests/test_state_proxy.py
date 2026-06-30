"""Minimal checks for StateProxyMixin delegation."""

from ui.state import AppState
from ui.state.proxy import StateProxyMixin


class _StubApp(StateProxyMixin):
    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}
        self.state = AppState.from_settings(self.settings)


def test_proxy_get_set_field():
    app = _StubApp()
    app.filter_year = 2024
    app.filter_month = 6
    assert app.filter_year == 2024
    assert app.state.filter_year == 2024
    assert app.filter_month == 6


def test_proxy_delegates_methods():
    app = _StubApp()
    assert app.is_mei_mode() is False
    app.app_mode = "mei"
    assert app.is_mei_mode() is True
    app.set_active_view_index(2)
    assert app.mei_view_index == 2


def test_proxy_unknown_attr_raises():
    app = _StubApp()
    try:
        _ = app.not_a_state_field
        raised = False
    except AttributeError:
        raised = True
    assert raised