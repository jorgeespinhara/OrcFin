"""Investment holding form — add/edit positions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import flet as ft

from core.db.repositories.investment_holdings import create_holding, update_holding
from core.integrations.funds.cvm_registry import lookup_fund_by_cnpj, search_funds
from core.models import InvestmentHolding
from core.network_policy import external_calls_allowed
from ui.personal.charts import PERSONAL_ACCENT
from ui.theme import active as theme_colors, field_params

ASSET_CLASSES = [
    ("stock", "Ação"),
    ("fii", "FII"),
    ("etf", "ETF"),
    ("fund", "Fundo (CNPJ)"),
    ("crypto", "Criptomoeda"),
    ("other", "Outro"),
]


def open_holding_form(app, *, holding: InvestmentHolding | None = None, on_saved=None) -> None:
    profile_id = app.get_view_profile_id()
    if not profile_id:
        app.show_snack("Selecione um perfil individual.", success=False)
        return

    is_edit = holding is not None
    selected_class = holding.asset_class if holding else "stock"
    fund_lookup_result: dict | None = None

    class_field = ft.Dropdown(
        label="Classe",
        value=selected_class,
        options=[ft.dropdown.Option(k, v) for k, v in ASSET_CLASSES],
        width=220,
        **field_params(accent=PERSONAL_ACCENT),
    )
    symbol_field = ft.TextField(
        label="Ticker",
        value=holding.symbol if holding else "",
        hint_text="Ex.: PETR4, HGLG11, BTC",
        visible=selected_class != "fund",
        **field_params(accent=PERSONAL_ACCENT),
    )
    cnpj_field = ft.TextField(
        label="CNPJ do fundo",
        value=holding.cnpj if holding else "",
        hint_text="00.000.000/0001-00",
        visible=selected_class == "fund",
        **field_params(accent=PERSONAL_ACCENT),
    )
    name_field = ft.TextField(
        label="Nome",
        value=holding.name if holding else "",
        **field_params(accent=PERSONAL_ACCENT),
    )
    qty_field = ft.TextField(
        label="Quantidade / cotas",
        value=str(holding.quantity) if holding else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_params(accent=PERSONAL_ACCENT),
    )
    cost_field = ft.TextField(
        label="Preço médio (R$)",
        value=str(holding.avg_cost) if holding else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        **field_params(accent=PERSONAL_ACCENT),
    )
    applied_field = ft.TextField(
        label="Data de aplicação",
        value=holding.applied_at.isoformat() if holding and holding.applied_at else "",
        hint_text="AAAA-MM-DD",
        **field_params(accent=PERSONAL_ACCENT),
    )
    broker_field = ft.TextField(
        label="Corretora / instituição",
        value=holding.broker if holding else "",
        **field_params(accent=PERSONAL_ACCENT),
    )
    notes_field = ft.TextField(
        label="Notas",
        value=holding.notes if holding else "",
        multiline=True,
        min_lines=2,
        **field_params(accent=PERSONAL_ACCENT),
    )
    fund_results = ft.Column(spacing=4, tight=True)
    fund_status = ft.Text("", size=11, color=theme_colors().text_muted)

    def toggle_fields():
        is_fund = class_field.value == "fund"
        symbol_field.visible = not is_fund
        cnpj_field.visible = is_fund
        app.page.update()

    class_field.on_change = lambda _: toggle_fields()

    def pick_fund(fund: dict):
        nonlocal fund_lookup_result
        fund_lookup_result = fund
        cnpj_field.value = fund.get("cnpj_display") or fund.get("cnpj", "")
        name_field.value = fund.get("name", "")
        fund_results.controls.clear()
        fund_status.value = f"Selecionado: {fund.get('name', '')}"
        app.page.update()

    def search_cvm(_=None):
        fund_results.controls.clear()
        if not external_calls_allowed(app.settings):
            fund_status.value = "Modo offline: busca CVM indisponível."
            app.page.update()
            return
        query = (cnpj_field.value or name_field.value or "").strip()
        if len(query) < 2:
            fund_status.value = "Digite ao menos 2 caracteres."
            app.page.update()
            return
        try:
            matches = search_funds(query, limit=8)
        except Exception as ex:
            fund_status.value = f"Erro na busca CVM: {ex}"
            app.page.update()
            return
        if not matches:
            fund_status.value = "Nenhum fundo encontrado."
            app.page.update()
            return
        fund_status.value = f"{len(matches)} resultado(s)"
        for fund in matches:
            fund_results.controls.append(
                ft.TextButton(
                    f"{fund.get('cnpj_display', '')} - {fund.get('name', '')[:60]}",
                    on_click=lambda _, f=fund: pick_fund(f),
                )
            )
        app.page.update()

    cnpj_field.on_submit = search_cvm

    def resolve_fund_name(cnpj: str) -> str:
        nonlocal fund_lookup_result
        if fund_lookup_result:
            return fund_lookup_result.get("name", "")
        if external_calls_allowed(app.settings):
            found = lookup_fund_by_cnpj(cnpj)
            if found:
                fund_lookup_result = found
                return found.get("name", "")
        return ""

    def save(_=None):
        asset_class = class_field.value or "stock"
        name = (name_field.value or "").strip()
        if not name and asset_class == "fund":
            cnpj_raw = (cnpj_field.value or "").strip()
            name = resolve_fund_name(cnpj_raw)
        if not name:
            app.show_snack("Informe o nome do ativo.", success=False)
            return
        try:
            qty = Decimal(str((qty_field.value or "0").replace(",", ".")))
            if qty <= 0:
                raise ValueError("quantidade")
            avg_cost = Decimal(str((cost_field.value or "0").replace(",", ".")))
            if avg_cost < 0:
                raise ValueError("custo")
        except Exception:
            app.show_snack("Quantidade e preço médio inválidos.", success=False)
            return

        applied_at = None
        raw_date = (applied_field.value or "").strip()
        if raw_date:
            try:
                applied_at = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                app.show_snack("Data inválida (use AAAA-MM-DD).", success=False)
                return

        from core.integrations.funds.cvm_utils import normalize_cnpj

        model = InvestmentHolding(
            id=holding.id if holding else None,
            profile_id=profile_id,
            asset_class=asset_class,
            symbol=(symbol_field.value or "").strip().upper() or None,
            cnpj=normalize_cnpj(cnpj_field.value) or None,
            name=name,
            quantity=qty,
            avg_cost=avg_cost,
            applied_at=applied_at,
            broker=(broker_field.value or "").strip() or None,
            notes=(notes_field.value or "").strip() or None,
        )
        if is_edit:
            update_holding(model)
            app.show_snack("Posição atualizada.")
        else:
            create_holding(model)
            app.show_snack("Posição adicionada.")
        app.close_modal()
        if on_saved:
            on_saved()
        else:
            app.refresh_current_view()

    actions = ft.Row(
        [
            ft.TextButton("Cancelar", on_click=lambda _: app.close_modal()),
            ft.ElevatedButton(
                "Salvar",
                icon=ft.Icons.SAVE,
                on_click=save,
                style=ft.ButtonStyle(bgcolor=PERSONAL_ACCENT, color=theme_colors().text_primary),
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    body = ft.Column(
        [
            class_field,
            symbol_field,
            ft.Row(
                [cnpj_field, ft.IconButton(ft.Icons.SEARCH, tooltip="Buscar na CVM", on_click=search_cvm)],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            fund_status,
            fund_results,
            name_field,
            ft.Row([qty_field, cost_field], spacing=12),
            applied_field,
            broker_field,
            notes_field,
            actions,
        ],
        spacing=10,
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )
    app.show_modal(body, title="Editar posição" if is_edit else "Nova posição")