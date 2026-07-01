"""MEI transaction list scoped to the PJ profile."""

from __future__ import annotations

import flet as ft

from ui.transactions import TransactionsView
from ui.mei.context import MeiContext, require_mei_ready
from ui.theme import active as theme_colors


class MeiLancamentosView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        self.ctx = MeiContext.load()

    def build(self) -> ft.Control:
        if setup := require_mei_ready(self.app, self.ctx):
            return setup

        c = theme_colors()
        hint = ft.Container(
            content=ft.Text(
                "Lançamentos do perfil MEI: despesas e receitas do CNPJ",
                size=12,
                color=c.mei_banner_text,
            ),
            bgcolor=c.mei_banner_bg,
            border=ft.Border.all(1, c.border),
            border_radius=8,
            padding=10,
        )
        tx_view = TransactionsView(self.app)
        body = tx_view.build()
        return ft.Column([hint, ft.Container(height=8), body], expand=True)