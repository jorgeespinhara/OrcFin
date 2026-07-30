"""Report charts and summary sections."""

from __future__ import annotations

import flet as ft

from core.domain.value_objects.money import format_brl
from core.engine.recurrence_detection import detect_recurring_transactions
from core.engine.reporting import get_top_expense_categories_with_trend
from core.engine.scenario_simulator import parse_adjustment_from_form, simulate_scenario
from core.engine.seasonal_analysis import get_seasonal_expense_comparison, get_seasonal_highlights
from ui.personal.charts import (
    category_trend_chart,
    scenario_comparison_chart,
    seasonal_comparison_chart,
    section_card,
)
from ui.theme import (
    active as theme_colors,
    collapsible_section,
    primary_button_style,
)


def mini_metric(label: str, value: str) -> ft.Column:
    c = theme_colors()
    return ft.Column(
        [
            ft.Text(label, size=12, color=c.text_muted, tooltip=label),
            ft.Text(
                value,
                size=18,
                weight=ft.FontWeight.BOLD,
                color=c.text_primary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                tooltip=value,
            ),
        ],
        spacing=4,
        tight=True,
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
            ft.Text(
                "Nenhuma despesa por categoria no período. Cadastre lançamentos para ver tendências.",
                color=c.text_muted,
                size=12,
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
                ft.Text(format_brl(h["reference_total"]), size=16, weight=ft.FontWeight.BOLD, color=tone),
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

    chips = (
        ft.Row(
            [_highlight_chip(h) for h in highlights],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        if highlights
        else ft.Text("Sem desvios relevantes neste ano.", size=12, color=c.text_muted)
    )

    return section_card(
        f"Comparativo sazonal · {anchor_year}",
        ft.Column(
            [
                ft.Text(
                    f"Barras laranja = {anchor_year}. Azul = média dos últimos anos no mesmo mês. "
                    "Percentual sob o mês é o desvio vs média (não precisa rolar 12 blocos).",
                    size=12,
                    color=c.text_muted,
                ),
                chips,
                seasonal_comparison_chart(seasonal, max_months=12),
            ],
            spacing=14,
            tight=True,
        ),
        # Fixed, short: full year visible without deep scroll
        height=340,
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
    result_container = ft.Container()
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
    income_f = ft.TextField(label="Δ receita mensal (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER)
    expense_f = ft.TextField(label="Δ despesa mensal (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER)
    onetime_in_f = ft.TextField(label="Receita única (R$)", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    onetime_out_f = ft.TextField(label="Despesa única (R$)", width=140, keyboard_type=ft.KeyboardType.NUMBER)

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
        delta = summary.get("delta_cumulative", 0)
        delta_color = c.success if float(delta) >= 0 else c.danger
        result_container.content = ft.Column(
            [
                ft.Text(
                    f"Saldo projetado: base {format_brl(summary.get('base_final_cumulative', 0))} "
                    f"→ cenário {format_brl(summary.get('scenario_final_cumulative', 0))}",
                    size=13,
                    color=c.text_secondary,
                ),
                ft.Text(
                    f"Diferença: {format_brl(delta)}",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=delta_color,
                ),
                scenario_comparison_chart(sim["base"], sim["scenario"]),
            ],
            spacing=10,
            tight=True,
        )
        result_container.update()

    body = ft.Column(
        [
            ft.Text(
                "Ajuste receitas/despesas e compare a projeção base com o cenário.",
                size=12,
                color=c.text_muted,
            ),
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
    recurrences = detect_recurring_transactions(profile_id, consolidated)[:8]
    if not recurrences:
        body = ft.Text(
            "Nenhuma recorrência detectada com os critérios atuais (≥3 meses, variação <10%).",
            color=c.text_muted,
            size=12,
        )
    else:
        rows = [
            ft.DataRow(
                cells=[
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
                        ft.Text(format_brl(r["average_amount"]), size=12, tooltip=format_brl(r["average_amount"]))
                    ),
                    ft.DataCell(ft.Text(f"{r['distinct_months']}m", size=12)),
                    ft.DataCell(ft.Text(f"{r['amount_deviation_pct']:.0f}%", size=12)),
                ]
            )
            for r in recurrences
        ]
        body = ft.Column(
            [
                ft.Text(
                    "Gastos/receitas repetidos com valor estável nos últimos meses.",
                    size=12,
                    color=c.text_muted,
                ),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Descrição")),
                        ft.DataColumn(ft.Text("Categoria")),
                        ft.DataColumn(ft.Text("Média")),
                        ft.DataColumn(ft.Text("Meses")),
                        ft.DataColumn(ft.Text("Var.")),
                    ],
                    rows=rows,
                    heading_row_color=c.surface_alt,
                    horizontal_lines=ft.border.BorderSide(0.5, c.border),
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
