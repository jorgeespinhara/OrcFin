"""Investment holding form — add/edit positions."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

import flet as ft

from core.db.repositories.investment_holdings import create_holding, update_holding
from core.domain.br_date import format_br_date, format_br_date_input, parse_br_date
from core.integrations.brokers import search_brokers
from core.integrations.funds.cvm_registry import lookup_fund_by_cnpj, search_funds
from core.integrations.quotes.ticker_registry import lookup_ticker_name, search_tickers
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
    initial_applied = holding.applied_at if holding else None
    selected_date = {"value": initial_applied}

    form_error = ft.Text("", size=12, color=theme_colors().error_text, visible=False)

    def show_form_error(msg: str) -> None:
        form_error.value = msg
        form_error.visible = bool(msg)
        app.page.update()

    def clear_form_error() -> None:
        show_form_error("")

    class_field = ft.RadioGroup(
        value=selected_class,
        content=ft.Row(
            [ft.Radio(value=key, label=label) for key, label in ASSET_CLASSES],
            wrap=True,
            spacing=8,
            run_spacing=4,
        ),
    )
    symbol_field = ft.TextField(
        label="Ticker",
        value=holding.symbol if holding else "",
        hint_text="Ex.: PETR4, HGLG11, BTC",
        visible=selected_class != "fund",
        on_change=lambda _: (clear_form_error(), refresh_ticker_suggestions()),
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
        on_change=lambda _: clear_form_error(),
        **field_params(accent=PERSONAL_ACCENT),
    )
    qty_field = ft.TextField(
        label="Quantidade / cotas",
        value=str(holding.quantity) if holding else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda _: clear_form_error(),
        **field_params(accent=PERSONAL_ACCENT),
    )
    cost_field = ft.TextField(
        label="Preço médio (R$)",
        value=str(holding.avg_cost) if holding else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda _: clear_form_error(),
        **field_params(accent=PERSONAL_ACCENT),
    )
    applied_field = ft.TextField(
        label="Data de aplicação",
        value=format_br_date(initial_applied),
        hint_text="DD/MM/AAAA",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        **field_params(accent=PERSONAL_ACCENT),
    )
    broker_field = ft.TextField(
        label="Corretora / instituição",
        value=holding.broker if holding else "",
        hint_text="Digite para sugerir",
        on_change=lambda _: (clear_form_error(), refresh_broker_suggestions()),
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
    ticker_results = ft.Column(spacing=4, tight=True)
    ticker_status = ft.Text("", size=11, color=theme_colors().text_muted)
    broker_results = ft.Column(spacing=4, tight=True)
    broker_status = ft.Text("", size=11, color=theme_colors().text_muted)

    def on_applied_typed(e):
        clear_form_error()
        masked = format_br_date_input(e.control.value or "")
        if e.control.value != masked:
            e.control.value = masked
        raw = re.sub(r"\D", "", masked)
        if len(raw) == 8:
            try:
                selected_date["value"] = parse_br_date(masked)
            except ValueError:
                selected_date["value"] = None
        else:
            selected_date["value"] = None
        app.page.update()

    applied_field.on_change = on_applied_typed

    def on_date_picked(_):
        picked = date_picker.value
        if picked is None:
            return
        if isinstance(picked, datetime):
            picked = picked.date()
        selected_date["value"] = picked
        applied_field.value = format_br_date(picked)
        clear_form_error()
        app.page.update()

    date_picker = ft.DatePicker(
        value=initial_applied or date.today(),
        first_date=date(1990, 1, 1),
        last_date=date.today(),
        entry_mode=ft.DatePickerEntryMode.CALENDAR,
        help_text="Selecione dia, mês e ano",
        confirm_text="Confirmar",
        cancel_text="Cancelar",
        on_change=on_date_picked,
    )
    if date_picker not in app.page.overlay:
        app.page.overlay.append(date_picker)

    def open_calendar(_=None):
        if selected_date["value"]:
            date_picker.value = selected_date["value"]
        app.page.show_dialog(date_picker)

    def toggle_fields():
        is_fund = class_field.value == "fund"
        symbol_field.visible = not is_fund
        cnpj_field.visible = is_fund
        ticker_results.controls.clear()
        ticker_status.value = ""
        fund_results.controls.clear()
        fund_status.value = ""
        clear_form_error()
        app.page.update()

    def pick_ticker(item: dict):
        symbol_field.value = item.get("symbol", "")
        label = (item.get("name") or "").strip()
        if not label:
            label = lookup_ticker_name(item.get("symbol", ""), class_field.value or "stock", app.settings)
        if label and not (name_field.value or "").strip():
            name_field.value = label
        ticker_results.controls.clear()
        ticker_status.value = f"Selecionado: {item.get('symbol', '')}"
        clear_form_error()
        app.page.update()

    def refresh_ticker_suggestions(_=None):
        ticker_results.controls.clear()
        asset_class = class_field.value or "stock"
        if asset_class == "fund":
            ticker_status.value = ""
            app.page.update()
            return
        query = (symbol_field.value or "").strip()
        if len(query) < 3:
            ticker_status.value = "Digite ao menos 3 letras para sugerir tickers."
            app.page.update()
            return
        try:
            matches = search_tickers(query, asset_class, app.settings, limit=8)
        except Exception as ex:
            ticker_status.value = f"Erro na busca: {ex}"
            app.page.update()
            return
        if not matches:
            ticker_status.value = "Nenhum ticker encontrado."
            app.page.update()
            return
        ticker_status.value = f"{len(matches)} sugestão(ões)"
        for item in matches:
            sym = item.get("symbol", "")
            label = item.get("name") or ""
            text = f"{sym} - {label}" if label else sym
            ticker_results.controls.append(
                ft.TextButton(text, on_click=lambda _, i=item: pick_ticker(i))
            )
        app.page.update()

    def pick_broker(name: str):
        broker_field.value = name
        broker_results.controls.clear()
        broker_status.value = f"Selecionado: {name}"
        clear_form_error()
        app.page.update()

    def refresh_broker_suggestions(_=None):
        broker_results.controls.clear()
        query = (broker_field.value or "").strip()
        if len(query) < 2:
            broker_status.value = ""
            app.page.update()
            return
        matches = search_brokers(query, limit=8)
        if not matches:
            broker_status.value = "Nenhuma corretora encontrada."
            app.page.update()
            return
        broker_status.value = f"{len(matches)} sugestão(ões)"
        for name in matches:
            broker_results.controls.append(
                ft.TextButton(name, on_click=lambda _, n=name: pick_broker(n))
            )
        app.page.update()

    def on_class_change(_):
        toggle_fields()
        refresh_ticker_suggestions()

    class_field.on_change = on_class_change

    def pick_fund(fund: dict):
        nonlocal fund_lookup_result
        fund_lookup_result = fund
        cnpj_field.value = fund.get("cnpj_display") or fund.get("cnpj", "")
        name_field.value = fund.get("name", "")
        fund_results.controls.clear()
        fund_status.value = f"Selecionado: {fund.get('name', '')}"
        clear_form_error()
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
        clear_form_error()
        asset_class = class_field.value or "stock"
        name = (name_field.value or "").strip()
        if not name and asset_class == "fund":
            cnpj_raw = (cnpj_field.value or "").strip()
            name = resolve_fund_name(cnpj_raw)
        if not name:
            show_form_error("Informe o nome do ativo.")
            return
        try:
            qty = Decimal(str((qty_field.value or "0").replace(",", ".")))
            if qty <= 0:
                raise ValueError("quantidade")
            avg_cost = Decimal(str((cost_field.value or "0").replace(",", ".")))
            if avg_cost < 0:
                raise ValueError("custo")
        except Exception:
            show_form_error("Quantidade e preço médio inválidos.")
            return

        applied_at = selected_date["value"]
        raw_date = (applied_field.value or "").strip()
        if raw_date and not applied_at:
            try:
                applied_at = parse_br_date(raw_date)
            except ValueError:
                show_form_error("Data inválida. Use DD/MM/AAAA.")
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
        try:
            if is_edit:
                update_holding(model)
                msg = "Posição atualizada."
            else:
                create_holding(model)
                msg = "Posição adicionada."
        except Exception as ex:
            show_form_error(f"Erro ao salvar: {ex}")
            return

        app.close_modal()
        app.show_snack(msg)
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
            ft.Text("Classe do ativo", size=12, color=theme_colors().text_muted),
            class_field,
            form_error,
            symbol_field,
            ticker_status,
            ticker_results,
            ft.Row(
                [cnpj_field, ft.IconButton(ft.Icons.SEARCH, tooltip="Buscar na CVM", on_click=search_cvm)],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            fund_status,
            fund_results,
            name_field,
            ft.Row([qty_field, cost_field], spacing=12),
            ft.Row(
                [
                    applied_field,
                    ft.IconButton(
                        ft.Icons.CALENDAR_MONTH,
                        tooltip="Abrir calendário",
                        icon_color=PERSONAL_ACCENT,
                        on_click=open_calendar,
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            broker_field,
            broker_status,
            broker_results,
            notes_field,
            actions,
        ],
        spacing=10,
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )
    app.show_modal(body, title="Editar posição" if is_edit else "Nova posição")