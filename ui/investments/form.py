"""Investment holding form — add/edit positions."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from decimal import Decimal

import flet as ft

from core.db.repositories.investment_holdings import create_holding, update_holding
from core.domain.br_date import format_br_date, format_br_date_input, parse_br_date
from core.integrations.brokers import search_brokers
from core.integrations.funds.cvm_registry import lookup_fund_by_cnpj, search_funds
from core.integrations.quotes.ticker_registry import lookup_ticker_name, search_tickers
from core.engine.portfolio_metrics import validate_holding_quantity
from core.models import InvestmentHolding
from core.network_policy import external_calls_allowed
from ui.personal.charts import PERSONAL_ACCENT
from ui.settings.helpers import _modal_dropdown
from ui.theme import active as theme_colors, field_params

_DEBOUNCE_SECS = 0.35


def _schedule_debounced(page, tokens: dict[str, int], key: str, fn) -> None:
    async def _wait():
        tokens[key] = tokens.get(key, 0) + 1
        token = tokens[key]
        await asyncio.sleep(_DEBOUNCE_SECS)
        if tokens.get(key) != token:
            return
        fn()

    page.run_task(_wait)


ASSET_CLASSES = [
    ("stock", "Ação"),
    ("fii", "FII"),
    ("etf", "ETF"),
    ("fund", "Fundo (CNPJ)"),
    ("crypto", "Criptomoeda"),
    ("other", "Outro"),
]


def _suggestion_row(label: str, on_pick) -> ft.Container:
    return ft.Container(
        content=ft.Text(label, size=13, color=theme_colors().text_primary),
        padding=ft.Padding(10, 8, 10, 8),
        border_radius=8,
        ink=True,
        on_click=lambda _: on_pick(),
    )


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
    debounce_tokens: dict[str, int] = {}

    form_error = ft.Text("", size=12, color=theme_colors().error_text, visible=False)

    def show_form_error(msg: str) -> None:
        form_error.value = msg
        form_error.visible = bool(msg)
        app.page.update()

    def clear_form_error() -> None:
        show_form_error("")

    class_field = _modal_dropdown(
        label="Tipo de investimento",
        value=selected_class,
        width=480,
        options=[ft.dropdown.Option(key, label) for key, label in ASSET_CLASSES],
    )
    symbol_field = ft.TextField(
        label="Ticker",
        value=holding.symbol if holding else "",
        hint_text="Ex.: PETR4, HGLG11, BTC",
        visible=selected_class != "fund",
        on_change=lambda _: (clear_form_error(), schedule_ticker_suggestions()),
        **field_params(accent=PERSONAL_ACCENT),
    )
    cnpj_field = ft.TextField(
        label="CNPJ do fundo",
        value=holding.cnpj if holding else "",
        hint_text="00.000.000/0001-00",
        visible=selected_class == "fund",
        on_change=lambda _: (clear_form_error(), schedule_cnpj_name_resolve()),
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
        on_change=lambda _: (clear_form_error(), schedule_broker_suggestions()),
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
        barrier_color=theme_colors().modal_scrim,
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
        fund_search_row.visible = is_fund
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

    def _apply_ticker_matches(matches: list[dict], asset_class: str, query: str) -> None:
        ticker_results.controls.clear()
        if asset_class == "fund":
            ticker_status.value = ""
            return
        if len(query) < 3:
            ticker_status.value = "Digite ao menos 3 letras para sugerir tickers."
            return
        if not matches:
            ticker_status.value = "Nenhum ticker encontrado."
            return
        ticker_status.value = f"{len(matches)} sugestão(ões)"
        for item in matches:
            sym = item.get("symbol", "")
            label = item.get("name") or ""
            text = f"{sym} - {label}" if label else sym
            ticker_results.controls.append(
                _suggestion_row(text, lambda i=item: pick_ticker(i))
            )

    async def _refresh_ticker_suggestions_async():
        asset_class = class_field.value or "stock"
        query = (symbol_field.value or "").strip()
        if asset_class == "fund":
            _apply_ticker_matches([], asset_class, query)
            app.page.update()
            return
        if len(query) < 3:
            _apply_ticker_matches([], asset_class, query)
            app.page.update()
            return
        try:
            matches = await asyncio.to_thread(
                search_tickers, query, asset_class, app.settings, limit=8
            )
        except Exception as ex:
            ticker_results.controls.clear()
            ticker_status.value = f"Erro na busca: {ex}"
            app.page.update()
            return
        _apply_ticker_matches(matches, asset_class, query)
        app.page.update()

    def refresh_ticker_suggestions(_=None):
        app.page.run_task(_refresh_ticker_suggestions_async)

    def schedule_ticker_suggestions(_=None):
        _schedule_debounced(app.page, debounce_tokens, "ticker", refresh_ticker_suggestions)

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
                _suggestion_row(name, lambda n=name: pick_broker(n))
            )
        app.page.update()

    def schedule_broker_suggestions(_=None):
        _schedule_debounced(app.page, debounce_tokens, "broker", refresh_broker_suggestions)

    def on_class_change(_):
        toggle_fields()
        schedule_ticker_suggestions()

    class_field.on_select = on_class_change

    def pick_fund(fund: dict):
        nonlocal fund_lookup_result
        fund_lookup_result = fund
        cnpj_field.value = fund.get("cnpj_display") or fund.get("cnpj", "")
        name_field.value = fund.get("name", "")
        fund_results.controls.clear()
        fund_status.value = f"Selecionado: {fund.get('name', '')}"
        clear_form_error()
        app.page.update()

    def _apply_fund_matches(matches: list[dict], query: str) -> None:
        fund_results.controls.clear()
        if len(query) < 2:
            fund_status.value = "Digite ao menos 2 caracteres."
            return
        if not matches:
            fund_status.value = "Nenhum fundo encontrado."
            return
        fund_status.value = f"{len(matches)} resultado(s)"
        for fund in matches:
            label = f"{fund.get('cnpj_display', '')} - {fund.get('name', '')[:60]}"
            fund_results.controls.append(
                _suggestion_row(label, lambda f=fund: pick_fund(f))
            )

    async def _search_cvm_async():
        fund_results.controls.clear()
        if not external_calls_allowed(app.settings):
            fund_status.value = "Modo offline: busca CVM indisponível."
            app.page.update()
            return
        query = (cnpj_field.value or name_field.value or "").strip()
        if len(query) < 2:
            _apply_fund_matches([], query)
            app.page.update()
            return
        fund_status.value = "Buscando na CVM..."
        app.page.update()
        try:
            matches = await asyncio.to_thread(search_funds, query, limit=8)
        except Exception as ex:
            fund_results.controls.clear()
            fund_status.value = f"Erro na busca CVM: {ex}"
            app.page.update()
            return
        _apply_fund_matches(matches, query)
        app.page.update()

    def search_cvm(_=None):
        app.page.run_task(_search_cvm_async)

    async def _resolve_cnpj_name_async():
        from core.integrations.funds.cvm_utils import normalize_cnpj

        if class_field.value != "fund":
            return
        if (name_field.value or "").strip():
            return
        cnpj_raw = (cnpj_field.value or "").strip()
        if len(normalize_cnpj(cnpj_raw)) != 14:
            return
        try:
            name = await asyncio.to_thread(resolve_fund_name, cnpj_raw)
        except Exception:
            return
        if name and not (name_field.value or "").strip():
            name_field.value = name
            app.page.update()

    def resolve_cnpj_name(_=None):
        app.page.run_task(_resolve_cnpj_name_async)

    def schedule_cnpj_name_resolve(_=None):
        _schedule_debounced(app.page, debounce_tokens, "cnpj_name", resolve_cnpj_name)

    cnpj_field.on_submit = search_cvm

    fund_search_row = ft.Row(
        [
            cnpj_field,
            ft.IconButton(
                ft.Icons.SEARCH,
                tooltip="Buscar na CVM",
                on_click=search_cvm,
            ),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        visible=selected_class == "fund",
    )

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
        symbol = (symbol_field.value or "").strip().upper()
        name = (name_field.value or "").strip()
        if not name and asset_class == "fund":
            cnpj_raw = (cnpj_field.value or "").strip()
            name = resolve_fund_name(cnpj_raw)
        elif not name and symbol:
            name = lookup_ticker_name(symbol, asset_class, app.settings) or symbol
        if not name:
            show_form_error("Informe o nome do ativo.")
            return
        try:
            qty = Decimal(str((qty_field.value or "0").replace(",", ".")))
            avg_cost = Decimal(str((cost_field.value or "0").replace(",", ".")))
            if avg_cost < 0:
                raise ValueError("custo")
        except Exception:
            show_form_error("Quantidade e preço médio inválidos.")
            return

        qty_error = validate_holding_quantity(qty, asset_class)
        if qty_error:
            show_form_error(qty_error)
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
        from core.services.portfolio_service import quotes_enabled, refresh_quotes

        model = InvestmentHolding(
            id=holding.id if holding else None,
            profile_id=profile_id,
            asset_class=asset_class,
            symbol=symbol or None,
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
        if on_saved:
            on_saved()
        else:
            app.refresh_current_view()
        app.show_snack(msg)

        async def _refresh_quotes_bg():
            if not quotes_enabled(app.settings):
                return
            try:
                await asyncio.to_thread(refresh_quotes, profile_id, app.settings)
            except Exception:
                pass

        app.page.run_task(_refresh_quotes_bg)

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

    form_fields = ft.Column(
        [
            class_field,
            form_error,
            symbol_field,
            ticker_status,
            ticker_results,
            fund_search_row,
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
        ],
        spacing=10,
        tight=True,
        scroll=ft.ScrollMode.AUTO,
    )
    app.show_modal(
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=form_fields, height=380),
                    actions,
                ],
                spacing=12,
                tight=True,
            ),
            width=520,
            padding=ft.Padding(4, 16, 4, 4),
        ),
        title="Editar posição" if is_edit else "Nova posição",
    )