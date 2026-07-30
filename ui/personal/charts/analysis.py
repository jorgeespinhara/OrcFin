"""Category trend and comparison charts."""

from __future__ import annotations

import flet as ft

from core.domain.month_format import chart_point_label
from core.domain.value_objects.money import format_brl
from ui.theme import active as theme_colors

from ui.personal.charts.constants import PERSONAL_ACCENT, EXPENSE_COLOR, PROJECTION_COLOR
from ui.personal.charts.helpers import _axis_label, _empty_chart_text, _muted_bar, readable_label
from ui.personal.charts.bars import _bar_row, horizontal_bar_chart


def category_trend_chart(trend: list, *, compact: bool = True) -> ft.Control:
    """Compact sparkline of recent months (default) or full horizontal bars."""
    if not trend:
        return _empty_chart_text("Sem histórico para esta categoria")

    if not compact:
        items = [
            {"label": p["label"], "value": p["total"], "color": EXPENSE_COLOR}
            for p in trend
        ]
        return horizontal_bar_chart(items, max_items=12, stacked_labels=False)

    points = list(trend)[-8:]
    values = [float(p.get("total", 0)) for p in points]
    max_val = max(values) if values else 1.0
    chart_h = 36
    bars = []
    for p, val in zip(points, values):
        h = max(3, int((val / max_val) * chart_h)) if max_val > 0 else 3
        label = p.get("label", "")
        tip = f"{label}: {format_brl(val)}"
        bars.append(
            ft.Container(
                content=ft.Container(
                    height=h,
                    bgcolor=EXPENSE_COLOR,
                    border_radius=3,
                    tooltip=tip,
                ),
                height=chart_h,
                width=14,
                alignment=ft.Alignment(0, 1),
                tooltip=tip,
                expand=True,
            )
        )
    return ft.Column(
        [
            ft.Row(bars, spacing=3, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row(
                [
                    ft.Text(points[0].get("label", ""), size=10, color=theme_colors().text_muted),
                    ft.Container(expand=True),
                    ft.Text(points[-1].get("label", ""), size=10, color=theme_colors().text_muted),
                ],
            ),
        ],
        spacing=4,
        tight=True,
    )


def seasonal_comparison_chart(data: dict, *, max_months: int = 12) -> ft.Control:
    """Grouped vertical columns: reference year vs multi-year average (compact YoY view)."""
    months = data.get("months", [])[:max_months]
    ref_year = data.get("reference_year", 0)
    if not months:
        return _empty_chart_text("Sem histórico sazonal")

    ref_values = [float(m["reference_total"]) for m in months]
    avg_values = [float(m["average"]) for m in months]
    max_val = max(ref_values + avg_values, default=0) or 1.0

    chart_h = 140
    bar_w = 10
    c = theme_colors()

    groups = []
    for m in months:
        ref = float(m["reference_total"])
        avg = float(m["average"])
        yoy = m.get("yoy_change_pct")
        vs_avg = m.get("vs_average_pct")

        ref_h = max(4, int((ref / max_val) * chart_h)) if max_val > 0 and ref > 0 else (2 if ref == 0 else 4)
        avg_h = max(4, int((avg / max_val) * chart_h)) if max_val > 0 and avg > 0 else (2 if avg == 0 else 4)

        ref_tip = f"{m['label']} {ref_year}: {format_brl(ref)}"
        avg_tip = f"{m['label']} média: {format_brl(avg)}"

        delta_color = c.text_muted
        delta_txt = "-"
        if vs_avg is not None:
            if vs_avg > 5:
                delta_color = c.danger
                delta_txt = f"↑{vs_avg:.0f}%"
            elif vs_avg < -5:
                delta_color = c.success
                delta_txt = f"↓{abs(vs_avg):.0f}%"
            else:
                delta_txt = f"{vs_avg:+.0f}%"
        elif yoy is not None:
            delta_color = c.danger if yoy > 5 else (c.success if yoy < -5 else c.text_muted)
            delta_txt = f"YoY {yoy:+.0f}%"

        groups.append(
            ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Container(
                                        height=ref_h,
                                        width=bar_w,
                                        bgcolor=EXPENSE_COLOR,
                                        border_radius=3,
                                    ),
                                    height=chart_h,
                                    alignment=ft.Alignment(0, 1),
                                    tooltip=ref_tip,
                                ),
                                ft.Container(
                                    content=ft.Container(
                                        height=avg_h,
                                        width=bar_w,
                                        bgcolor=PROJECTION_COLOR,
                                        border_radius=3,
                                        border=ft.Border.all(1, PROJECTION_COLOR),
                                        opacity=0.75,
                                    ),
                                    height=chart_h,
                                    alignment=ft.Alignment(0, 1),
                                    tooltip=avg_tip,
                                ),
                            ],
                            spacing=3,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        border=ft.Border.only(bottom=ft.BorderSide(1, c.border)),
                        padding=ft.Padding.only(bottom=4),
                    ),
                    ft.Text(
                        m["label"],
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=c.text_primary,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        delta_txt,
                        size=10,
                        color=delta_color,
                        weight=ft.FontWeight.W_500,
                        text_align=ft.TextAlign.CENTER,
                        tooltip=f"vs média: {format_brl(ref)} · {format_brl(avg)}",
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
                tight=True,
            )
        )

    legend = ft.Row(
        [
            ft.Container(width=12, height=12, bgcolor=EXPENSE_COLOR, border_radius=3),
            ft.Text(str(ref_year), size=12, color=c.text_secondary, weight=ft.FontWeight.W_500),
            ft.Container(width=8),
            ft.Container(width=12, height=12, bgcolor=PROJECTION_COLOR, border_radius=3, opacity=0.75),
            ft.Text("Média histórica", size=12, color=c.text_secondary, weight=ft.FontWeight.W_500),
            ft.Container(expand=True),
            ft.Text("▲ acima da média · ▼ abaixo", size=11, color=c.text_muted),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Column(
        [
            legend,
            ft.Row(
                groups,
                spacing=4,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
        ],
        spacing=12,
        tight=True,
    )


def scenario_comparison_chart(base: list, scenario: list) -> ft.Control:
    """Compact vertical comparison of base vs scenario cumulative path."""
    if not base and not scenario:
        return _empty_chart_text("Execute a simulação para ver o gráfico")

    points = base or scenario
    points = points[:12]
    values = [float(p.get("projected_cumulative", 0)) for p in points]
    scen_values = [float(p.get("projected_cumulative", 0)) for p in (scenario or [])[:12]]
    max_val = max(max(abs(v) for v in values + scen_values), 1.0) if (values or scen_values) else 1.0

    chart_h = 120
    bar_w = 9
    c = theme_colors()
    groups = []
    for i, point in enumerate(points):
        label = chart_point_label(point)
        b_val = float(base[i]["projected_cumulative"]) if i < len(base) else 0
        s_val = float(scenario[i]["projected_cumulative"]) if scenario and i < len(scenario) else 0
        b_h = max(4, int((abs(b_val) / max_val) * chart_h))
        s_h = max(4, int((abs(s_val) / max_val) * chart_h))
        groups.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Container(
                                    height=b_h, width=bar_w, bgcolor=PERSONAL_ACCENT, border_radius=3
                                ),
                                height=chart_h,
                                alignment=ft.Alignment(0, 1),
                                tooltip=f"Base {label}: {format_brl(b_val)}",
                            ),
                            ft.Container(
                                content=ft.Container(
                                    height=s_h,
                                    width=bar_w,
                                    bgcolor=PROJECTION_COLOR,
                                    border_radius=3,
                                    border=ft.Border.all(1, PROJECTION_COLOR),
                                ),
                                height=chart_h,
                                alignment=ft.Alignment(0, 1),
                                tooltip=f"Cenário {label}: {format_brl(s_val)}",
                            ),
                        ],
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text(label, size=10, color=c.text_muted, text_align=ft.TextAlign.CENTER),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
                tight=True,
            )
        )

    legend = ft.Row(
        [
            ft.Container(width=12, height=12, bgcolor=PERSONAL_ACCENT, border_radius=3),
            ft.Text("Base", size=12, color=c.text_secondary),
            ft.Container(width=8),
            ft.Container(width=12, height=12, bgcolor=PROJECTION_COLOR, border_radius=3),
            ft.Text("Cenário", size=12, color=c.text_secondary),
        ],
        spacing=6,
    )
    return ft.Column(
        [
            legend,
            ft.Row(groups, spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ],
        spacing=10,
        tight=True,
    )


def net_worth_evolution_chart(evolution: list) -> ft.Control:
    if not evolution:
        return _empty_chart_text("Cadastre ativos e passivos em Configurações")

    items = [
        {"label": p.get("label", ""), "value": p["net_worth"], "color": PERSONAL_ACCENT}
        for p in evolution
    ]
    return horizontal_bar_chart(items, max_items=12, stacked_labels=True)


def budget_status_chart(budgets: list) -> ft.Control:
    if not budgets:
        return ft.Container(
            content=ft.Text(
                "Nenhum orçamento definido. Configure em Configurações → Orçamentos.",
                color=theme_colors().text_muted,
                size=12,
            ),
            alignment=ft.Alignment(0, 0),
        )

    rows = []
    for b in budgets[:8]:
        pct = float(b.get("percentage", 0))
        status = b.get("status", "ok")
        c = theme_colors()
        color = c.success if status == "ok" else (c.warning if status == "warning" else c.danger)
        cat_label = f"{b.get('icon', '')} {b['category_name']}".strip()
        rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            readable_label(cat_label, size=13, expand=True, max_lines=2),
                            ft.Text(
                                f"{pct:.0f}%",
                                size=13,
                                color=color,
                                weight=ft.FontWeight.BOLD,
                                width=48,
                                text_align=ft.TextAlign.RIGHT,
                                tooltip=f"{pct:.0f}%",
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
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
                spacing=6,
                tight=True,
            )
        )

    return ft.Column(rows, spacing=12, tight=True)
