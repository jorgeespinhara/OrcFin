"""MEI shell navigation."""

from __future__ import annotations

import flet as ft

from ui.mei.home import MeiHomeView
from ui.mei.vendas import MeiVendasView
from ui.mei.obrigacoes import MeiObrigacoesView
from ui.mei.notas import MeiNotasView
from ui.mei.resultado import MeiResultadoView
from ui.mei.lancamentos import MeiLancamentosView


def view_from_map(index: int, view_map: dict, default_cls, app):
    """Resolve view class by index — shared by personal and MEI routers."""
    return view_map.get(index, default_cls)(app)


MEI_VIEW_MAP = {
    0: MeiHomeView,
    1: MeiVendasView,
    2: MeiObrigacoesView,
    3: MeiNotasView,
    4: MeiResultadoView,
    5: MeiLancamentosView,
}


def mei_destinations() -> list[ft.NavigationRailDestination]:
    return [
        ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Início"),
        ft.NavigationRailDestination(icon=ft.Icons.STOREFRONT_OUTLINED, selected_icon=ft.Icons.STOREFRONT, label="Vendas"),
        ft.NavigationRailDestination(icon=ft.Icons.FACT_CHECK_OUTLINED, selected_icon=ft.Icons.FACT_CHECK, label="Obrigações"),
        ft.NavigationRailDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="Notas"),
        ft.NavigationRailDestination(icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS, label="Resultado"),
        ft.NavigationRailDestination(icon=ft.Icons.RECEIPT_LONG_OUTLINED, selected_icon=ft.Icons.RECEIPT_LONG, label="Lançamentos"),
    ]


def get_mei_view(index: int, app):
    return view_from_map(index, MEI_VIEW_MAP, MeiHomeView, app)