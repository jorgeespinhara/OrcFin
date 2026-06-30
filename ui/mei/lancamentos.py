"""MEI transaction list scoped to the PJ profile."""

from __future__ import annotations

import flet as ft

from ui.transactions import TransactionsView
from ui.mei.constants import MEI_ACCENT_DARK
from ui.mei.context import MeiContext, require_mei_ready


class MeiLancamentosView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        hint = ft.Container(
            content=ft.Text(
                "Lançamentos do perfil MEI apenas — despesas e receitas do CNPJ",
                size=12,
                color="#FDE68A",
            ),
            bgcolor=MEI_ACCENT_DARK,
            border_radius=8,
            padding=10,
        )
        tx_view = TransactionsView(self.app)
        body = tx_view.build()
        return ft.Column([hint, ft.Container(height=8), body], expand=True)