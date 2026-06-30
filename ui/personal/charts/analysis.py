"""Category trend and comparison charts."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, EXPENSE_COLOR, PROJECTION_COLOR
from ui.personal.charts.helpers import _axis_label, _empty_chart_text, _muted_bar
from ui.personal.charts.bars import _bar_row
from ui.personal.charts.bars import horizontal_bar_chart

def category_trend_chart(trend: list) -> ft.Control:
    if not trend:
        return _empty_chart_text("Sem histórico para esta categoria")

    items = [
        {"label": p["label"], "value": p["total"], "color": EXPENSE_COLOR}
        for p in trend
    ]
    return horizontal_bar_chart(items, max_items=12)

def seasonal_comparison_chart(data: dict, *, max_months: int = 12) -> ft.Control:
    """Multi-year bars for reference year vs prior years (same calendar months)."""
    months = data.get("months", [])[:max_months]
    ref_year = data.get("reference_year", 0)
    if not months:
        return _empty_chart_text("Sem histórico sazonal")

    ref_values = [float(m["reference_total"]) for m in months]
    avg_values = [float(m["average"]) for m in months]
    max_val = max(ref_values + avg_values, default=0) or 1.0

    rows = []
    for m in months:
        ref = float(m["reference_total"])
        avg = float(m["average"])
        yoy = m.get("yoy_change_pct")
        subtitle = f"YoY {yoy:+.0f}%" if yoy is not None else ""
        rows.append(
            ft.Column(
                [
                    _axis_label(m["label"], size=12),
                    _bar_row(m["label"], ref, max_val, EXPENSE_COLOR, format_brl(ref), subtitle=subtitle),
                    _bar_row("Média", avg, max_val, "#6366F1", format_brl(avg), dashed=True, subtitle=f"{ref_year}"),
                ],
                spacing=2,
            )
        )
    return ft.Column(rows, spacing=6)

def scenario_comparison_chart(base: list, scenario: list) -> ft.Control:
    if not base and not scenario:
        return _empty_chart_text("Execute a simulação para ver o gráfico")

    points = base or scenario
    values = [float(p.get("projected_cumulative", 0)) for p in points]
    scen_values = [float(p.get("projected_cumulative", 0)) for p in (scenario or [])]
    max_val = max(max(values + scen_values, default=0), 1.0)

    rows = []
    for i, point in enumerate(points[:12]):
        label = chart_point_label(point)
        b_val = float(base[i]["projected_cumulative"]) if i < len(base) else 0
        s_val = float(scenario[i]["projected_cumulative"]) if i < len(scenario) else 0
        rows.append(
            ft.Column(
                [
                    _axis_label(label, size=12),
                    _bar_row("Base", abs(b_val), max_val, PERSONAL_ACCENT, format_brl(b_val)),
                    _bar_row("Cenário", abs(s_val), max_val, PROJECTION_COLOR, format_brl(s_val), dashed=True),
                ],
                spacing=2,
            )
        )
    return ft.Column(rows, spacing=6)

def net_worth_evolution_chart(evolution: list) -> ft.Control:
    if not evolution:
        return _empty_chart_text("Cadastre ativos e passivos em Configurações")

    items = [
        {"label": p.get("label", ""), "value": p["net_worth"], "color": PERSONAL_ACCENT}
        for p in evolution
    ]
    return horizontal_bar_chart(items, max_items=12)

def budget_status_chart(budgets: list) -> ft.Control:
    if not budgets:
        return ft.Container(
            content=ft.Text(
                "Nenhum orçamento definido. Configure em Configurações → Orçamentos.",
                color=theme_colors().text_muted,
                size=12,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

    rows = []
    for b in budgets[:8]:
        pct = float(b.get("percentage", 0))
        status = b.get("status", "ok")
        color = "#22C55E" if status == "ok" else ("#F59E0B" if status == "warning" else "#EF4444")
        rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                f"{b.get('icon', '')} {b['category_name'][:26]}",
                                size=14,
                                expand=True,
                                color=theme_colors().text_primary,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                f"{pct:.0f}%",
                                size=14,
                                color=color,
                                weight=ft.FontWeight.BOLD,
                                width=56,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                        ],
                    ),
                    ft.ProgressBar(
                        value=min(pct / 100, 1.0),
                        color=color,
                        bgcolor=_muted_bar(),
                        height=10,
                        border_radius=5,
                    ),
                    ft.Text(
                        f"{format_brl(b['spent'])} / {format_brl(b['limit'])}",
                        size=13,
                        color=theme_colors().text_secondary,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=8,
            )
        )

    return ft.Column(rows, spacing=12)
