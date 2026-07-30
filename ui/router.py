"""View routing — personal and MEI navigation."""

from __future__ import annotations

import flet as ft

from ui.dashboard import DashboardView
from ui.transactions import TransactionsView
from ui.credit_cards import CreditCardsView
from ui.investments import InvestmentsView
from ui.reports import ReportsView
from ui.settings import SettingsView
from ui.mei_router import get_mei_view, mei_destinations


PERSONAL_VIEW_MAP = {
    0: DashboardView,
    1: TransactionsView,
    2: CreditCardsView,
    3: InvestmentsView,
    4: ReportsView,
    5: SettingsView,
}


def personal_destinations() -> list[ft.NavigationRailDestination]:
    return [
        ft.NavigationRailDestination(
            icon=ft.Icons.DASHBOARD_OUTLINED,
            selected_icon=ft.Icons.DASHBOARD,
            label="Dashboard",
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.RECEIPT_LONG_OUTLINED,
            selected_icon=ft.Icons.RECEIPT_LONG,
            label="Lançamentos",
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.CREDIT_CARD_OUTLINED,
            selected_icon=ft.Icons.CREDIT_CARD,
            label="Cartões",
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.TRENDING_UP_OUTLINED,
            selected_icon=ft.Icons.TRENDING_UP,
            label="Investimentos",
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.ANALYTICS_OUTLINED,
            selected_icon=ft.Icons.ANALYTICS,
            label="Relatórios & IA",
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.SETTINGS_OUTLINED,
            selected_icon=ft.Icons.SETTINGS,
            label="Configurações",
        ),
    ]


def view_from_map(index: int, view_map: dict, default_cls: type, app):
    cls = view_map.get(index, default_cls)
    return cls(app)


def get_view(index: int, app):
    """Resolve personal-mode view by index."""
    return view_from_map(index, PERSONAL_VIEW_MAP, DashboardView, app)


def resolve_view(app, index: int):
    """Resolve view for current app mode."""
    if app.is_mei_mode():
        return get_mei_view(index, app)
    return get_view(index, app)


def switch_view(app, index: int) -> None:
    """Navigate to view index and render in content area."""
    if hasattr(app, "clean_transient_ui"):
        app.clean_transient_ui()
    app.set_active_view_index(index)
    if hasattr(app, "nav_rail"):
        app.nav_rail.selected_index = index

    view = resolve_view(app, index)
    try:
        app.content_area.content = view.build()
    except Exception as ex:
        import logging

        logging.getLogger(__name__).exception("Failed to build view %s", index)
        c = __import__("ui.theme", fromlist=["active"]).active()
        app.content_area.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Não foi possível carregar esta tela.", size=16, color=c.text_primary),
                    ft.Text(str(ex), size=12, color=c.error_text, selectable=True),
                ],
                spacing=8,
                tight=True,
            ),
            padding=24,
        )
        if hasattr(app, "show_snack"):
            app.show_snack(f"Erro ao abrir a tela: {ex}", success=False)
    app.page.update()