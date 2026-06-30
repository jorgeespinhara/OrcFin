"""Report charts and summary sections."""

from __future__ import annotations

import flet as ft


def mini_metric(view, label: str, value: str) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, size=11, color=theme_colors().text_muted),
            ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=theme_colors().text_primary),
        ],
        spacing=4,
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

    if not top_categories:
        return section_card(
            "Tendência por categoria",
            ft.Text(
                "Nenhuma despesa por categoria no período. Cadastre lançamentos para ver tendências.",
                color=theme_colors().text_muted,
                size=12,
            ),
            expand=True,
            height=height,
        )

    trend_blocks = []
    for item in top_categories:
        trend_blocks.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                f"{item['icon']} {item['name'][:36]}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=theme_colors().text_primary,
                                expand=True,
                            ),
                            ft.Text(
                                format_brl(item["total"]),
                                size=11,
                                color=theme_colors().text_muted,
                            ),
                        ],
                    ),
                    category_trend_chart(item["trend"]),
                ],
                spacing=6,
            )
        )

    return section_card(
        "Tendência por categoria",
        ft.Column(
            [
                ft.Text(
                    "Categorias com lançamentos no período (maiores despesas primeiro)",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                *trend_blocks,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        height=height,
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
    highlight_text = ", ".join(
        f"{h['label']} ({format_brl(h['reference_total'])})" for h in highlights
    ) or "Sem destaques"

    return section_card(
        f"Comparativo sazonal de despesas — {anchor_year}",
        ft.Column(
            [
                ft.Text(
                    f"Maiores desvios vs média histórica: {highlight_text}",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                seasonal_comparison_chart(seasonal, max_months=12),
            ],
            spacing=10,
        ),
        height=320,
    )

def build_scenario_section(
    self,
    profile_id: int | None,
    consolidated: bool,
    anchor_year: int,
    anchor_month: int,
    ) -> ft.Container:
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
    income_f = ft.TextField(label="Δ receita mensal (R$)", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    expense_f = ft.TextField(label="Δ despesa mensal (R$)", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    onetime_in_f = ft.TextField(label="Receita única (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER)
    onetime_out_f = ft.TextField(label="Despesa única (R$)", width=160, keyboard_type=ft.KeyboardType.NUMBER)

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
        result_container.content = ft.Column(
            [
                ft.Text(
                    f"Saldo projetado: base {format_brl(summary.get('base_final_cumulative', 0))} "
                    f"→ cenário {format_brl(summary.get('scenario_final_cumulative', 0))} "
                    f"({format_brl(delta)})",
                    size=12,
                    color=theme_colors().text_secondary,
                ),
                scenario_comparison_chart(sim["base"], sim["scenario"]),
            ],
            spacing=10,
        )
        result_container.update()

    return section_card(
        "Simulador E se...",
        ft.Column(
            [
                ft.Text("Ajuste receitas/despesas e compare projeção base vs cenário.", size=11, color=theme_colors().text_muted),
                ft.Row(
                    [months_dd, income_f, expense_f, onetime_in_f, onetime_out_f,
                     ft.ElevatedButton("Simular", icon=ft.Icons.PLAY_ARROW, on_click=run_sim)],
                    wrap=True,
                    spacing=8,
                ),
                result_container,
            ],
            spacing=12,
        ),
        height=360,
    )

def build_recurrence_section(
    self,
    profile_id: int | None,
    consolidated: bool,
    ) -> ft.Container:
    recurrences = detect_recurring_transactions(profile_id, consolidated)[:8]
    if not recurrences:
        body = ft.Text("Nenhuma recorrência detectada com os critérios atuais (≥3 meses, variação <10%).", color=theme_colors().text_muted, size=12)
    else:
        rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(r["description"][:40], color=theme_colors().text_primary, size=11)),
                ft.DataCell(ft.Text(r["category_name"][:20], color=theme_colors().text_muted, size=11)),
                ft.DataCell(ft.Text(format_brl(r["average_amount"]), size=11)),
                ft.DataCell(ft.Text(f"{r['distinct_months']}m", size=11)),
                ft.DataCell(ft.Text(f"{r['amount_deviation_pct']:.0f}%", size=11)),
            ])
            for r in recurrences
        ]
        body = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Descrição")),
                ft.DataColumn(ft.Text("Categoria")),
                ft.DataColumn(ft.Text("Média")),
                ft.DataColumn(ft.Text("Meses")),
                ft.DataColumn(ft.Text("Var.")),
            ],
            rows=rows,
            heading_row_color=theme_colors().surface_alt,
            horizontal_lines=ft.border.BorderSide(0.5, theme_colors().border),
        )

    return section_card(
        "Recorrências detectadas",
        ft.Column(
            [
                ft.Text("Gastos/receitas repetidos com valor estável nos últimos meses.", size=11, color=theme_colors().text_muted),
                body,
            ],
            spacing=10,
        ),
    )
