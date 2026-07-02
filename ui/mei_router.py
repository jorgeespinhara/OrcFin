"""MEI shell navigation."""

from __future__ import annotations

import flet as ft

from core.mei_operational import enabled_modules
from ui.mei.home import MeiHomeView
from ui.mei.vendas import MeiVendasView
from ui.mei.pedidos import MeiPedidosView
from ui.mei.payables import MeiPayablesView
from ui.mei.recorrentes import MeiRecorrentesView
from ui.mei.estoque import MeiEstoqueView
from ui.mei.obrigacoes import MeiObrigacoesView
from ui.mei.notas import MeiNotasView
from ui.mei.resultado import MeiResultadoView
from ui.mei.lancamentos import MeiLancamentosView


def _nav_spec(operational_profile: str | None) -> list[tuple[type, str, str, str]]:
    items: list[tuple[type, str, str, str]] = [
        (MeiHomeView, ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "Início"),
        (MeiVendasView, ft.Icons.STOREFRONT_OUTLINED, ft.Icons.STOREFRONT, "Vendas"),
    ]
    if "orders" in enabled_modules(operational_profile):
        items.extend(
            [
                (MeiPedidosView, ft.Icons.INVENTORY_2_OUTLINED, ft.Icons.INVENTORY_2, "Pedidos"),
                (MeiPayablesView, ft.Icons.ENGINEERING_OUTLINED, ft.Icons.ENGINEERING, "Terceiros"),
            ]
        )
    if "recurring_billing" in enabled_modules(operational_profile):
        items.append(
            (MeiRecorrentesView, ft.Icons.REPEAT_OUTLINED, ft.Icons.REPEAT, "Recorrentes"),
        )
    if "inventory" in enabled_modules(operational_profile):
        items.append(
            (MeiEstoqueView, ft.Icons.INVENTORY_OUTLINED, ft.Icons.INVENTORY, "Estoque"),
        )
    items.extend(
        [
            (MeiObrigacoesView, ft.Icons.FACT_CHECK_OUTLINED, ft.Icons.FACT_CHECK, "Obrigações"),
            (MeiNotasView, ft.Icons.DESCRIPTION_OUTLINED, ft.Icons.DESCRIPTION, "Notas"),
            (MeiResultadoView, ft.Icons.INSIGHTS_OUTLINED, ft.Icons.INSIGHTS, "Resultado"),
            (MeiLancamentosView, ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG, "Lançamentos"),
        ]
    )
    return items


def mei_destinations(operational_profile: str | None = None) -> list[ft.NavigationRailDestination]:
    return [
        ft.NavigationRailDestination(icon=icon, selected_icon=selected, label=label)
        for _, icon, selected, label in _nav_spec(operational_profile)
    ]


def mei_tab_index(operational_profile: str | None, label: str) -> int:
    for idx, (_, _, _, nav_label) in enumerate(_nav_spec(operational_profile)):
        if nav_label == label:
            return idx
    return 0


def get_mei_view(index: int, app):
    profile = app._mei_operational_profile() if hasattr(app, "_mei_operational_profile") else None
    spec = _nav_spec(profile)
    idx = min(max(index, 0), len(spec) - 1)
    return spec[idx][0](app)