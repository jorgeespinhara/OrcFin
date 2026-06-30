"""Credit cards management and statement import."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.domain.value_objects.money import format_brl
from core.db.repositories.credit_cards import (
    create_credit_card,
    delete_credit_card,
    get_card_spending_summary,
    get_credit_cards,
    update_credit_card,
)
from core.models import CreditCard
from ui.import_flow import open_import_flow
from ui.theme import text_field as themed_field, dropdown as themed_dropdown
from ui.personal.charts import PERSONAL_ACCENT
from ui.personal.period_filter import build_period_filter, period_label
from ui.theme import active as theme_colors, title_text, body_text

CARD_NETWORKS = [
    "Visa",
    "Mastercard",
    "American Express",
    "Elo",
    "Hipercard",
    "Outro",
]

BANK_PRESETS = [
    "Nubank",
    "Itaú",
    "Bradesco",
    "BTG",
    "Santander",
    "Inter",
    "C6 Bank",
    "Outro",
]


class CreditCardsView:
    def __init__(self, app: "OrcFinApp"):
        self.app = app
        profile_id = app.get_view_profile_id()
        self.cards = get_credit_cards(profile_id) if profile_id else []

    def build(self) -> ft.Control:
        context_label = self.app.get_view_context_label()
        header = ft.Row(
            [
                ft.Column(
                    [
                        title_text("Cartões"),
                        body_text(
                            f"{context_label} • {period_label(self.app.filter_year, self.app.filter_month)}",
                            size=13,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                build_period_filter(self.app),
                ft.ElevatedButton(
                    "Novo cartão",
                    icon=ft.Icons.ADD_CARD,
                    on_click=lambda _: self._open_card_form(),
                    style=ft.ButtonStyle(bgcolor="#8B5CF6", color=ft.Colors.WHITE),
                ),
                ft.OutlinedButton(
                    "Importar fatura PDF",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=self._import_invoice,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        if self.app.is_consolidated:
            body = ft.Container(
                padding=24,
                content=ft.Text(
                    "Selecione um perfil individual para gerenciar cartões.",
                    color=ft.Colors.GREY_400,
                    size=14,
                ),
            )
        elif not self.cards:
            body = ft.Container(
                padding=32,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.CREDIT_CARD, size=48, color="#8B5CF6"),
                        ft.Text("Nenhum cartão cadastrado", size=16, color=theme_colors().text_primary),
                        ft.Text(
                            "Cadastre um cartão ou importe uma fatura PDF (Nubank, etc.) "
                            "para detectar banco, bandeira e lançamentos automaticamente.",
                            size=13,
                            color=ft.Colors.GREY_400,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
            )
        else:
            body = ft.Column(
                [self._build_card_tile(card) for card in self.cards],
                spacing=12,
            )

        return ft.Column([header, ft.Container(height=16), body], expand=True, scroll=ft.ScrollMode.AUTO)

    def _build_card_tile(self, card: CreditCard) -> ft.Container:
        year = self.app.filter_year or date.today().year
        month = self.app.filter_month or date.today().month
        summary = get_card_spending_summary(card.id, year, month)

        network_icon = {
            "Visa": "💳",
            "Mastercard": "💳",
            "American Express": "🅰️",
            "Elo": "💳",
        }.get(card.network, "💳")

        return ft.Container(
            padding=20,
            bgcolor=theme_colors().surface,
            border_radius=16,
            border=ft.Border.all(1, card.color or "#8B5CF6"),
            content=ft.Row(
                [
                    ft.Container(
                        width=4,
                        height=72,
                        bgcolor=card.color or "#8B5CF6",
                        border_radius=4,
                    ),
                    ft.Column(
                        [
                            ft.Text(card.name, size=18, weight=ft.FontWeight.BOLD, color=theme_colors().text_primary),
                            ft.Text(
                                f"{network_icon} {card.bank} • {card.network}"
                                + (f" •••• {card.last_four}" if card.last_four else ""),
                                size=12,
                                color=ft.Colors.GREY_400,
                            ),
                            ft.Text(
                                f"Gastos no período: {format_brl(summary['total_expense'])} "
                                f"({summary['transaction_count']} lanç.)",
                                size=12,
                                color=ft.Colors.GREY_300,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_color="#14B8A6",
                        tooltip="Editar cartão",
                        on_click=lambda e, c=card: self._open_card_form(c),
                    ),
                    ft.IconButton(
                        ft.Icons.UPLOAD_FILE,
                        icon_color="#8B5CF6",
                        tooltip="Importar fatura deste cartão",
                        on_click=lambda e, c=card: self._import_invoice_for_card(c),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color="#EF4444",
                        tooltip="Excluir cartão",
                        on_click=lambda e, cid=card.id: self._delete_card(cid),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _open_card_form(self, existing: CreditCard | None = None):
        profile_id = self.app.get_view_profile_id()
        if not profile_id:
            self.app.show_snack("Selecione um perfil individual", success=False)
            return

        _accent = PERSONAL_ACCENT
        _detail_w = 168
        name_field = themed_field(
            accent=_accent,
            label="Nome do cartão",
            value=existing.name if existing else None,
            expand=True,
        )
        bank_dd = themed_dropdown(
            accent=_accent,
            label="Banco",
            value=existing.bank if existing else "Nubank",
            options=[ft.dropdown.Option(b, b) for b in BANK_PRESETS],
            expand=True,
        )
        network_dd = themed_dropdown(
            accent=_accent,
            label="Bandeira",
            value=existing.network if existing else "Mastercard",
            options=[ft.dropdown.Option(n, n) for n in CARD_NETWORKS],
            width=200,
        )
        last_four = themed_field(
            accent=_accent,
            label="Final do cartão",
            value=existing.last_four if existing else None,
            max_length=4,
            width=_detail_w,
        )
        limit_field = themed_field(
            accent=_accent,
            label="Limite (R$)",
            value=str(existing.credit_limit) if existing and existing.credit_limit else None,
            width=_detail_w,
        )
        due_day = themed_field(
            accent=_accent,
            label="Dia vencimento",
            value=str(existing.due_day) if existing and existing.due_day else None,
            width=_detail_w,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save(_):
            if not name_field.value or not bank_dd.value:
                self.app.show_snack("Preencha nome e banco", success=False)
                return
            limit_val = None
            if limit_field.value:
                try:
                    limit_val = Decimal(limit_field.value.replace(",", "."))
                except Exception:
                    self.app.show_snack("Limite inválido", success=False)
                    return
            due_val = int(due_day.value) if due_day.value and due_day.value.isdigit() else None
            payload = CreditCard(
                id=existing.id if existing else None,
                profile_id=profile_id,
                name=name_field.value.strip(),
                bank=bank_dd.value,
                network=network_dd.value or "Mastercard",
                last_four=(last_four.value or "").strip() or None,
                credit_limit=limit_val,
                due_day=due_val,
            )
            if existing:
                update_credit_card(payload)
                self.app.show_snack("Cartão atualizado")
            else:
                create_credit_card(payload)
                self.app.show_snack("Cartão cadastrado")
            self.app.close_modal()
            self.app.refresh_current_view()

        self.app.show_modal(
            ft.Column(
                [
                    ft.Row([name_field], spacing=12),
                    ft.Row([bank_dd, network_dd], spacing=12),
                    ft.Row(
                        [last_four, limit_field, due_day],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row(
                        [
                            ft.TextButton("Cancelar", on_click=lambda _: self.app.close_modal()),
                            ft.ElevatedButton(
                                "Salvar",
                                on_click=save,
                                style=ft.ButtonStyle(bgcolor="#8B5CF6", color=ft.Colors.WHITE),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=16,
                tight=True,
            ),
            title="Editar cartão" if existing else "Novo cartão",
        )

    def _delete_card(self, card_id: int):
        def do_delete(_):
            delete_credit_card(card_id)
            self.app.close_modal()
            self.app.show_snack("Cartão removido")
            self.app.refresh_current_view()

        self.app.show_modal(
            ft.Column(
                [
                    ft.Text("Excluir este cartão? Os lançamentos permanecem, mas sem vínculo ao cartão.", size=13),
                    ft.Row(
                        [
                            ft.TextButton("Cancelar", on_click=lambda _: self.app.close_modal()),
                            ft.ElevatedButton(
                                "Excluir",
                                on_click=do_delete,
                                style=ft.ButtonStyle(bgcolor="#EF4444", color=ft.Colors.WHITE),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title="Confirmar exclusão",
        )

    def _import_invoice(self, _):
        open_import_flow(self.app)

    def _import_invoice_for_card(self, card: CreditCard):
        open_import_flow(self.app, preferred_card_id=card.id)