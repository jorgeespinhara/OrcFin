"""Dashboard detail sections — goals, due dates, and insights."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import flet as ft

from core.db.repositories.goals import get_active_goals
from core.db.repositories.net_worth import get_net_worth_evolution, get_net_worth_totals
from core.domain.value_objects.money import format_brl
from core.engine.due_dates import get_upcoming_due_dates
from core.engine.local_insights import get_local_finance_insights
from ui.dashboard.cards import build_projection_metric_card, mini_patrimony
from ui.personal.charts import PERSONAL_ACCENT, net_worth_evolution_chart, projection_forecast_chart, section_card
from ui.theme import active as theme_colors, field_params

def build_projection_section(view, detail: dict) -> ft.Control:
    income_total = detail.get("projected_income_total", 0)
    expense_total = detail.get("projected_expense_total", 0)
    net_total = detail.get("projected_net_total", 0)
    months = detail.get("months_ahead", view.app.projection_months_ahead)
    basis = detail.get("basis_label", "")

    input_h = 48
    months_field = ft.TextField(
        value=str(months),
        width=120,
        height=input_h,
        keyboard_type=ft.KeyboardType.NUMBER,
        max_length=2,
        hint_text="1 a 12",
        text_size=14,
        **field_params(accent=PERSONAL_ACCENT),
    )
    months_control = ft.Column(
        [
            ft.Text("Meses à frente", size=12, color=theme_colors().text_muted),
            months_field,
        ],
        spacing=4,
        tight=True,
    )

    def apply_projection_months(_=None):
        raw = (months_field.value or "").strip()
        if not raw.isdigit():
            view.app.show_snack("Informe um número entre 1 e 12", success=False)
            return
        chosen = max(1, min(12, int(raw)))
        months_field.value = str(chosen)
        if chosen != view.app.projection_months_ahead:
            view.app.set_projection_months_ahead(chosen)
            view.app.refresh_current_view()

    months_field.on_submit = apply_projection_months

    header_row = ft.Row(
        [
            ft.Column(
                [
                    ft.Text("Projeção financeira", size=20, weight=ft.FontWeight.BOLD, color=theme_colors().text_primary),
                    ft.Text(basis, size=12, color=theme_colors().text_muted),
                ],
                spacing=4,
                expand=True,
            ),
            ft.Row(
                [
                    months_control,
                    ft.ElevatedButton(
                        "Aplicar",
                        icon=ft.Icons.CHECK,
                        height=input_h,
                        on_click=apply_projection_months,
                        style=ft.ButtonStyle(
                            bgcolor=PERSONAL_ACCENT,
                            color=theme_colors().text_primary,
                            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
                        ),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    metrics = ft.Row(
        [
            build_projection_metric_card(
                f"Receitas previstas ({months}m)",
                format_brl(income_total),
                f"Média/mês: {format_brl(detail.get('average_monthly_income', 0))}",
                ft.Icons.TRENDING_UP,
                "#22C55E",
            ),
            build_projection_metric_card(
                f"Despesas previstas ({months}m)",
                format_brl(expense_total),
                f"Média/mês: {format_brl(detail.get('average_monthly_expense', 0))}",
                ft.Icons.TRENDING_DOWN,
                "#F97316",
            ),
            build_projection_metric_card(
                f"Saldo previsto ({months}m)",
                format_brl(net_total),
                "Receitas − despesas no horizonte escolhido",
                ft.Icons.SHOW_CHART,
                "#6366F1" if net_total >= 0 else "#EF4444",
            ),
        ],
        spacing=16,
    )

    chart_height = 300 if months <= 6 else 320

    return ft.Column(
        [
            header_row,
            ft.Container(height=16),
            metrics,
            ft.Container(height=16),
            section_card(
                f"Próximos {months} meses: receita, despesa e saldo",
                projection_forecast_chart(detail.get("monthly_points", [])),
                height=chart_height,
                scroll_content=False,
                expand=True,
            ),
        ],
        spacing=4,
    )

def build_insight_card(view, current: dict, projection_detail: dict) -> ft.Container:
    net = current["net_savings"]
    rate = current["savings_rate"]

    if net > 0 and rate >= 20:
        message = "Excelente! Sua taxa de poupança está saudável. Considere investir o excedente."
        color = "#22C55E"
    elif net > 0:
        message = "Bom ritmo. Pequenos ajustes nas despesas podem elevar sua taxa de poupança."
        color = "#14B8A6"
    else:
        message = "Atenção: Despesas superando receitas no período. Revisar gastos fixos é prioridade."
        color = "#EF4444"

    if projection_detail.get("has_history"):
        horizon = projection_detail.get("months_ahead", 3)
        message += (
            f" Projeção {horizon} meses: receitas {format_brl(projection_detail.get('projected_income_total', 0))}, "
            f"despesas {format_brl(projection_detail.get('projected_expense_total', 0))}, "
            f"saldo {format_brl(projection_detail.get('projected_net_total', 0))}."
        )

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LIGHTBULB_OUTLINED, color=color, size=28),
                ft.Column(
                    [
                        ft.Text("Leitura do período", size=13, color=theme_colors().text_muted),
                        ft.Text(message, size=13, color=theme_colors().text_primary),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=16,
        ),
        padding=20,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=ft.Border.all(1, "#334155"),
    )

def build_due_dates_section(view) -> ft.Control:
    items = get_upcoming_due_dates(
        view.app.get_view_profile_id(),
        view.app.is_consolidated,
    )
    if not items:
        return ft.Container()
    rows = []
    kind_icon = {"card": ft.Icons.CREDIT_CARD, "das": ft.Icons.FACT_CHECK, "recurring": ft.Icons.REPEAT}
    for item in items:
        amt = f" • {format_brl(item['amount'])}" if item.get("amount") else ""
        rows.append(
            ft.Row(
                [
                    ft.Icon(kind_icon.get(item["kind"], ft.Icons.EVENT), color="#14B8A6", size=18),
                    ft.Text(item["date"].strftime("%d/%m"), size=12, color=theme_colors().text_muted, width=48),
                    ft.Text(f"{item['label']}{amt}", size=12, color=theme_colors().text_primary, expand=True),
                ],
                spacing=8,
            )
        )
    return section_card("Próximos vencimentos (45 dias)", ft.Column(rows, spacing=6))

def build_local_insights_section(view) -> ft.Control:
    tips = get_local_finance_insights(
        profile_id=view.app.get_view_profile_id(),
        consolidated=view.app.is_consolidated,
        year=view.data.get("period_year"),
        month=view.data.get("period_month") or date.today().month,
    )
    rows = [ft.Text(t, size=12, color=theme_colors().text_secondary) for t in tips]
    return section_card("Análises locais (offline)", ft.Column(rows, spacing=6))

def build_net_worth_section(view) -> ft.Control:
    if view.app.is_consolidated:
        return ft.Container()

    profile_id = view.app.get_view_profile_id()
    if not profile_id:
        return ft.Container()

    totals = get_net_worth_totals(profile_id)
    evolution = get_net_worth_evolution(profile_id)
    if totals["total_assets"] == 0 and totals["total_liabilities"] == 0:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color="#14B8A6", size=20),
                    ft.Text(
                        "Patrimônio: cadastre ativos e passivos em Configurações.",
                        size=12,
                        color=theme_colors().text_muted,
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            bgcolor=theme_colors().surface,
            border_radius=12,
        )

    return section_card(
        "Patrimônio líquido",
        ft.Column(
            [
                ft.Row(
                    [
                        mini_patrimony("Ativos", format_brl(totals["total_assets"]), "#22C55E"),
                        mini_patrimony("Passivos", format_brl(totals["total_liabilities"]), "#EF4444"),
                        mini_patrimony("Líquido", format_brl(totals["net_worth"]), "#14B8A6"),
                    ],
                    spacing=24,
                    wrap=True,
                ),
                net_worth_evolution_chart(evolution),
            ],
            spacing=12,
        ),
        height=220,
    )

def build_goals_section(view) -> ft.Container:
    goals = get_active_goals()

    if not goals:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FLAG_OUTLINED, color="#14B8A6", size=20),
                    ft.Text("Nenhuma meta ativa. Crie em Configurações → Metas Financeiras.", size=12, color=theme_colors().text_muted),
                ],
                spacing=8,
            ),
            padding=16,
            bgcolor=theme_colors().surface,
            border_radius=12,
        )

    goal_cards = []
    for goal in goals[:3]:
        current = Decimal(str(goal.get("current_amount", 0)))
        target = Decimal(str(goal.get("target_amount", 1)))
        pct = min(float((current / target) * 100), 100) if target > 0 else 0
        progress_color = "#22C55E" if pct >= 100 else ("#14B8A6" if pct > 60 else "#F97316")

        goal_cards.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(goal["name"], size=12, weight=ft.FontWeight.W_600, expand=True),
                                ft.Text(f"{pct:.0f}%", size=11, color=progress_color, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        ft.ProgressBar(value=pct / 100, color=progress_color, bgcolor="#334155", height=6),
                        ft.Row(
                            [
                                ft.Text(f"R$ {float(current):,.0f}", size=10, color=theme_colors().text_muted),
                                ft.Text(f"Meta: R$ {float(target):,.0f}", size=10, color=theme_colors().text_muted),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=4,
                ),
                padding=12,
                bgcolor=theme_colors().surface_alt,
                border_radius=10,
                expand=True,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FLAG_OUTLINED, color="#14B8A6", size=18),
                        ft.Text("Metas Financeiras Ativas", size=13, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                    ],
                    spacing=8,
                ),
                ft.Row(goal_cards, spacing=12) if goal_cards else ft.Text("Nenhuma meta ativa", color=theme_colors().text_muted),
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor=theme_colors().surface,
        border_radius=12,
    )
