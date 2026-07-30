"""Report charts and summary sections."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

import flet as ft

from core.domain.value_objects.money import format_brl
from core.engine.recurrence_detection import detect_recurring_transactions
from core.engine.reporting import get_current_month_summary, get_top_expense_categories_with_trend
from core.engine.scenario_simulator import parse_adjustment_from_form, simulate_scenario
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights
from ui.personal.charts import (
    category_trend_chart,
    scenario_comparison_chart,
    seasonal_comparison_chart,
    section_card,
)
from ui.settings.helpers import on_surface_button_style
from ui.theme import (
    active as theme_colors,
    collapsible_section,
    format_change,
    primary_button_style,
)


def _go_transactions(app) -> None:
    from ui.router import switch_view

    switch_view(app, 1)


def _compact_empty(
    *,
    icon: str,
    message: str,
    action_label: str | None = None,
    on_action: Callable | None = None,
) -> ft.Container:
    c = theme_colors()
    row: list[ft.Control] = [
        ft.Icon(icon, color=c.accent, size=20),
        ft.Text(message, size=12, color=c.text_muted, expand=True),
    ]
    if action_label and on_action:
        row.append(
            ft.TextButton(
                action_label,
                on_click=lambda _: on_action(),
                style=on_surface_button_style(),
            )
        )
    return ft.Container(
        content=ft.Row(row, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=12,
    )


def mini_metric(
    label: str,
    value: str,
    *,
    color: str | None = None,
    subtitle: str | None = None,
    on_click: Callable | None = None,
    tooltip: str | None = None,
) -> ft.Control:
    c = theme_colors()
    value_color = color or c.text_primary
    body: list[ft.Control] = [
        ft.Text(label, size=12, color=c.text_muted, tooltip=label),
        ft.Text(
            value,
            size=18,
            weight=ft.FontWeight.BOLD,
            color=value_color,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            tooltip=value,
        ),
    ]
    if subtitle:
        body.append(
            ft.Text(
                subtitle,
                size=11,
                color=c.text_muted,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=subtitle,
            )
        )
    col = ft.Column(body, spacing=2, tight=True)
    if on_click is None:
        return col
    return ft.Container(
        content=col,
        on_click=lambda _: on_click(),
        ink=True,
        tooltip=tooltip or f"Ver {label.lower()}",
        padding=ft.Padding(8, 6, 8, 6),
        border_radius=8,
    )


def build_ytd_card(
    view,
    ytd: dict,
    *,
    title: str,
    prev_ytd: dict | None = None,
) -> ft.Container:
    c = theme_colors()
    net = ytd["net_savings"]
    rate = float(ytd.get("savings_rate") or 0)
    net_color = c.success if float(net) >= 0 else c.danger
    rate_color = c.success if rate >= 20 else (c.warning if rate >= 0 else c.danger)

    def _yoy_subtitle(key: str) -> str | None:
        if not prev_ytd:
            return None
        cur = float(ytd.get(key) or 0)
        prev = float(prev_ytd.get(key) or 0)
        if prev == 0:
            return None
        pct = ((cur - prev) / abs(prev)) * 100
        return format_change(pct).replace("vs período anterior", "vs ano anterior")

    tx_count = int(ytd.get("transaction_count") or 0)
    if tx_count == 0 and float(ytd.get("total_income") or 0) == 0 and float(
        ytd.get("total_expense") or 0
    ) == 0:
        body = _compact_empty(
            icon=ft.Icons.INSIGHTS_OUTLINED,
            message="Sem lançamentos neste período para montar o resumo.",
            action_label="Ir para lançamentos",
            on_action=lambda: _go_transactions(view.app),
        )
    else:
        body = ft.Row(
            [
                mini_metric(
                    "Receita",
                    format_brl(ytd["total_income"]),
                    color=c.income,
                    subtitle=_yoy_subtitle("total_income"),
                    on_click=lambda: _go_transactions(view.app),
                    tooltip="Ver lançamentos",
                ),
                mini_metric(
                    "Despesa",
                    format_brl(ytd["total_expense"]),
                    color=c.expense,
                    subtitle=_yoy_subtitle("total_expense"),
                    on_click=lambda: _go_transactions(view.app),
                    tooltip="Ver lançamentos",
                ),
                mini_metric(
                    "Economia",
                    format_brl(net),
                    color=net_color,
                    subtitle=_yoy_subtitle("net_savings"),
                ),
                mini_metric(
                    "Taxa de poupança",
                    f"{rate}%",
                    color=rate_color,
                    subtitle="Na ou acima da meta 20%" if rate >= 20 else "Meta de referência: 20%",
                ),
            ],
            spacing=16,
            wrap=True,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=c.text_primary),
                body,
            ],
            spacing=14,
            tight=True,
        ),
        padding=20,
        bgcolor=c.surface,
        border_radius=16,
        border=ft.Border.all(1, c.border),
    )


def build_category_trend_card(
    self,
    profile_id: int | None,
    consolidated: bool,
    anchor_year: int,
    anchor_month: int,
    height: int = 240,
) -> ft.Container:
    top_categories = get_top_expense_categories_with_trend(
        profile_id=profile_id,
        consolidated=consolidated,
        end_year=anchor_year,
        end_month=anchor_month,
        months_back=8,
        limit=4,
    )
    c = theme_colors()

    if not top_categories:
        return section_card(
            "Tendência por categoria",
            _compact_empty(
                icon=ft.Icons.CATEGORY_OUTLINED,
                message="Nenhuma despesa por categoria no período.",
                action_label="Ir para lançamentos",
                on_action=lambda: _go_transactions(self.app),
            ),
            expand=True,
            height=height,
        )

    trend_blocks = []
    for item in top_categories:
        name = f"{item['icon']} {item['name']}".strip()
        trend_blocks.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                name,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=c.text_primary,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=name,
                            ),
                            ft.Text(
                                format_brl(item["total"]),
                                size=12,
                                color=c.text_muted,
                                tooltip=format_brl(item["total"]),
                            ),
                        ],
                    ),
                    category_trend_chart(item["trend"], compact=True),
                ],
                spacing=4,
                tight=True,
            )
        )

    return section_card(
        "Tendência por categoria",
        ft.Column(
            [
                ft.Text(
                    "Maiores despesas e evolução recente (sparkline)",
                    size=12,
                    color=c.text_muted,
                ),
                *trend_blocks,
            ],
            spacing=12,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        height=height,
    )


def _highlight_chip(h: dict) -> ft.Container:
    c = theme_colors()
    pct = h.get("vs_average_pct")
    if pct is not None and pct > 0:
        tone = c.danger
        badge = f"↑ {pct:.0f}% vs média"
    elif pct is not None and pct < 0:
        tone = c.success
        badge = f"↓ {abs(pct):.0f}% vs média"
    else:
        tone = c.accent
        badge = "destaque"
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(h["label"], size=13, weight=ft.FontWeight.W_600, color=c.text_primary),
                ft.Text(
                    format_brl(h["reference_total"]),
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=tone,
                ),
                ft.Text(badge, size=11, color=tone),
            ],
            spacing=2,
            tight=True,
        ),
        padding=12,
        bgcolor=c.surface_alt,
        border=ft.Border.all(1, tone),
        border_radius=10,
        expand=True,
    )


def build_seasonal_section(
    self,
    profile_id: int | None,
    consolidated: bool,
    anchor_year: int,
) -> ft.Container:
    seasonal = get_seasonal_expense_comparison(
        profile_id=profile_id,
        consolidated=consolidated,
        reference_year=anchor_year,
        years_back=3,
    )
    highlights = get_seasonal_highlights(seasonal, top_n=3)
    c = theme_colors()
    months_data = seasonal.get("months") or []

    if not months_data:
        return section_card(
            f"Comparativo sazonal · {anchor_year}",
            _compact_empty(
                icon=ft.Icons.CALENDAR_MONTH,
                message="Sem histórico sazonal suficiente.",
                action_label="Ir para lançamentos",
                on_action=lambda: _go_transactions(self.app),
            ),
            height=120,
            scroll_content=False,
        )

    chips = (
        ft.Row(
            [_highlight_chip(h) for h in highlights],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        if highlights
        else ft.Text("Sem desvios relevantes neste ano.", size=12, color=c.text_muted)
    )

    show_full = {"v": False}
    chart_host = ft.Container()
    toggle_btn = ft.TextButton(
        "Ver ano completo",
        icon=ft.Icons.UNFOLD_MORE,
        style=on_surface_button_style(),
    )

    def render_chart():
        months = 12 if show_full["v"] else 6
        chart_host.content = seasonal_comparison_chart(seasonal, max_months=months)
        toggle_btn.text = "Ver só 6 meses" if show_full["v"] else "Ver ano completo"
        toggle_btn.icon = ft.Icons.UNFOLD_LESS if show_full["v"] else ft.Icons.UNFOLD_MORE

    def toggle(_):
        show_full["v"] = not show_full["v"]
        render_chart()
        self.app.page.update()

    toggle_btn.on_click = toggle
    render_chart()

    return section_card(
        f"Comparativo sazonal · {anchor_year}",
        ft.Column(
            [
                ft.Text(
                    f"Barras laranja = {anchor_year}. Azul = média dos últimos anos no mesmo mês. "
                    "Percentual sob o mês é o desvio vs média.",
                    size=12,
                    color=c.text_muted,
                ),
                chips,
                chart_host,
                ft.Row(
                    [ft.Container(expand=True), toggle_btn],
                    alignment=ft.MainAxisAlignment.END,
                )
                if len(months_data) > 6
                else ft.Container(),
            ],
            spacing=12,
            tight=True,
        ),
        height=320,
        scroll_content=False,
    )


def build_scenario_section(
    self,
    profile_id: int | None,
    consolidated: bool,
    anchor_year: int,
    anchor_month: int,
) -> ft.Control:
    c = theme_colors()
    result_container = ft.Container(
        content=_compact_empty(
            icon=ft.Icons.SCIENCE_OUTLINED,
            message="Preencha um ajuste e clique Simular — ou use um preset.",
        )
    )
    months_dd = ft.Dropdown(
        label="Horizonte",
        width=140,
        value="12",
        options=[
            ft.dropdown.Option("12", "12 meses"),
            ft.dropdown.Option("24", "24 meses"),
            ft.dropdown.Option("36", "36 meses"),
        ],
    )
    income_f = ft.TextField(
        label="Δ receita mensal (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER
    )
    expense_f = ft.TextField(
        label="Δ despesa mensal (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER
    )
    onetime_in_f = ft.TextField(
        label="Receita única (R$)", width=140, keyboard_type=ft.KeyboardType.NUMBER
    )
    onetime_out_f = ft.TextField(
        label="Despesa única (R$)", width=140, keyboard_type=ft.KeyboardType.NUMBER
    )

    def _clear_fields():
        income_f.value = ""
        expense_f.value = ""
        onetime_in_f.value = ""
        onetime_out_f.value = ""

    def apply_preset(kind: str):
        _clear_fields()
        summary = get_current_month_summary(profile_id, consolidated)
        if kind == "cut10":
            exp = float(summary.get("total_expense") or 0)
            expense_f.value = f"{-round(exp * 0.10, 2):.2f}"
        elif kind == "plus500":
            income_f.value = "500"
        elif kind == "bonus":
            onetime_in_f.value = "1000"
        self.app.page.update()

    def run_sim(_):
        months = int(months_dd.value or "12")
        adj = parse_adjustment_from_form(
            "Ajuste do usuário",
            income_delta=income_f.value or "0",
            expense_delta=expense_f.value or "0",
            one_time_income=onetime_in_f.value or "0",
            one_time_expense=onetime_out_f.value or "0",
        )
        sim = simulate_scenario(
            profile_id=profile_id,
            consolidated=consolidated,
            months_ahead=months,
            adjustments=[adj],
            end_year=anchor_year,
            end_month=anchor_month,
        )
        summary = sim["summary"]
        base_final = summary.get("base_final_cumulative", 0)
        scen_final = summary.get("scenario_final_cumulative", 0)
        delta = summary.get("delta_cumulative", 0)
        delta_color = c.success if float(delta) >= 0 else c.danger
        result_container.content = ft.Column(
            [
                ft.Row(
                    [
                        mini_metric("Base", format_brl(base_final)),
                        mini_metric("Cenário", format_brl(scen_final)),
                        mini_metric(
                            "Diferença",
                            format_brl(delta),
                            color=delta_color,
                            subtitle=f"Horizonte {months}m",
                        ),
                    ],
                    spacing=24,
                    wrap=True,
                ),
                scenario_comparison_chart(sim["base"], sim["scenario"]),
            ],
            spacing=12,
            tight=True,
        )
        result_container.update()

    presets = ft.Row(
        [
            ft.OutlinedButton(
                "−10% despesas",
                icon=ft.Icons.TRENDING_DOWN,
                on_click=lambda _: apply_preset("cut10"),
                style=on_surface_button_style(),
            ),
            ft.OutlinedButton(
                "+R$ 500 renda",
                icon=ft.Icons.TRENDING_UP,
                on_click=lambda _: apply_preset("plus500"),
                style=on_surface_button_style(),
            ),
            ft.OutlinedButton(
                "Bônus R$ 1.000",
                icon=ft.Icons.CARD_GIFTCARD,
                on_click=lambda _: apply_preset("bonus"),
                style=on_surface_button_style(),
            ),
        ],
        spacing=8,
        wrap=True,
    )

    body = ft.Column(
        [
            ft.Text(
                "Ajuste receitas/despesas e compare a projeção base com o cenário.",
                size=12,
                color=c.text_muted,
            ),
            ft.Text("Presets", size=12, weight=ft.FontWeight.W_600, color=c.text_secondary),
            presets,
            ft.Row(
                [
                    months_dd,
                    income_f,
                    expense_f,
                    onetime_in_f,
                    onetime_out_f,
                    ft.ElevatedButton(
                        "Simular",
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=run_sim,
                        style=primary_button_style(),
                    ),
                ],
                wrap=True,
                spacing=8,
            ),
            result_container,
        ],
        spacing=12,
        tight=True,
    )
    return collapsible_section(
        "Simulador E se…",
        body,
        expanded=False,
        subtitle="Projeção base vs cenário com seus ajustes",
    )


def build_recurrence_section(
    self,
    profile_id: int | None,
    consolidated: bool,
) -> ft.Control:
    c = theme_colors()
    recurrences = detect_recurring_transactions(profile_id, consolidated)
    # Impact = média × meses distintos (maior peso financeiro primeiro)
    recurrences = sorted(
        recurrences,
        key=lambda r: float(r["average_amount"]) * int(r["distinct_months"]),
        reverse=True,
    )[:8]

    if not recurrences:
        body = _compact_empty(
            icon=ft.Icons.REPEAT,
            message="Nenhuma recorrência detectada (≥3 meses, variação <10%).",
            action_label="Ir para lançamentos",
            on_action=lambda: _go_transactions(self.app),
        )
    else:
        rows = []
        for r in recurrences:
            is_expense = str(r.get("type", "")).lower() in ("expense", "despesa")
            type_icon = ft.Icons.ARROW_DOWNWARD if is_expense else ft.Icons.ARROW_UPWARD
            type_color = c.expense if is_expense else c.income
            type_label = "Despesa" if is_expense else "Receita"
            impact = float(r["average_amount"]) * int(r["distinct_months"])
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.Icon(type_icon, size=14, color=type_color),
                                    ft.Text(type_label, size=11, color=type_color, width=56),
                                ],
                                spacing=4,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                r["description"],
                                color=c.text_primary,
                                size=12,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=r["description"],
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                r["category_name"],
                                color=c.text_muted,
                                size=12,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=r["category_name"],
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                format_brl(r["average_amount"]),
                                size=12,
                                tooltip=format_brl(r["average_amount"]),
                            )
                        ),
                        ft.DataCell(ft.Text(f"{r['distinct_months']}m", size=12)),
                        ft.DataCell(
                            ft.Text(
                                format_brl(impact),
                                size=12,
                                tooltip=f"Impacto ≈ média × {r['distinct_months']} meses",
                            )
                        ),
                        ft.DataCell(ft.Text(f"{r['amount_deviation_pct']:.0f}%", size=12)),
                    ]
                )
            )
        body = ft.Column(
            [
                ft.Text(
                    "Padrões locais nos lançamentos (não enviados à IA). Ordenado por impacto.",
                    size=12,
                    color=c.text_muted,
                ),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Tipo")),
                        ft.DataColumn(ft.Text("Descrição")),
                        ft.DataColumn(ft.Text("Categoria")),
                        ft.DataColumn(ft.Text("Média")),
                        ft.DataColumn(ft.Text("Meses")),
                        ft.DataColumn(ft.Text("Impacto")),
                        ft.DataColumn(ft.Text("Var.")),
                    ],
                    rows=rows,
                    heading_row_color=c.surface_alt,
                    horizontal_lines=ft.border.BorderSide(0.5, c.border),
                ),
                ft.Row(
                    [
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Ver lançamentos",
                            icon=ft.Icons.RECEIPT_LONG,
                            on_click=lambda _: _go_transactions(self.app),
                            style=on_surface_button_style(),
                        ),
                    ]
                ),
            ],
            spacing=10,
            tight=True,
        )

    return collapsible_section(
        "Recorrências detectadas",
        body,
        expanded=bool(recurrences),
        subtitle="Padrões estáveis nos lançamentos",
    )


def build_more_analyses(
    view,
    *,
    profile_id: int | None,
    consolidated: bool,
    anchor_year: int,
    anchor_month: int,
) -> ft.Control:
    """Seasonal + scenario + recurrence under progressive disclosure."""
    body = ft.Column(
        [
            build_seasonal_section(view, profile_id, consolidated, anchor_year),
            ft.Container(height=12),
            build_scenario_section(
                view, profile_id, consolidated, anchor_year, anchor_month
            ),
            ft.Container(height=12),
            build_recurrence_section(view, profile_id, consolidated),
        ],
        spacing=0,
        tight=True,
    )
    return collapsible_section(
        "Mais análises",
        body,
        expanded=False,
        subtitle="Sazonal, simulador e recorrências",
    )
