"""Dashboard detail sections — goals, due dates, and insights."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

import flet as ft

from core.db.repositories.goals import get_active_goals
from core.db.repositories.net_worth import get_net_worth_evolution, get_net_worth_totals
from core.services.portfolio_service import get_portfolio_summary
from core.domain.value_objects.money import format_brl
from core.engine.due_dates import get_upcoming_due_dates
from core.db.repositories.dismissed_insights import dismiss_insight
from core.engine.decisions import get_decision_cards

from core.engine.local_insights import get_local_finance_insights
from core.i18n import t as tr
from ui.dashboard.cards import build_projection_metric_card, mini_patrimony
from ui.personal.charts import (
    PERSONAL_ACCENT,
    horizontal_bar_chart,
    net_worth_evolution_chart,
    projection_forecast_chart,
    section_card,
)
from ui.settings.helpers import on_surface_button_style
from ui.theme import active as theme_colors, field_params, primary_button_style, signed_label, status_color


def _compact_empty(
    *,
    icon: str,
    message: str,
    action_label: str | None = None,
    on_action: Callable | None = None,
) -> ft.Container:
    """Inline empty row for dashboard sections (lighter than full empty_state)."""
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


def build_projection_section(view, detail: dict) -> ft.Control:
    c = theme_colors()
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
        hint_text="1 a 12",
        text_size=14,
        **field_params(accent=PERSONAL_ACCENT),
    )
    months_control = ft.Column(
        [
            ft.Text(tr("dash.months_ahead"), size=12, color=c.text_muted),
            months_field,
        ],
        spacing=4,
        tight=True,
    )

    def apply_projection_months(_=None):
        raw = (months_field.value or "").strip()
        if not raw.isdigit():
            view.app.show_snack(tr("dash.months_invalid"), success=False)
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
                    ft.Text(tr("dash.projection_title"), size=18, weight=ft.FontWeight.BOLD, color=c.text_primary),
                    ft.Text(basis, size=12, color=c.text_muted),
                ],
                spacing=4,
                expand=True,
            ),
            ft.Row(
                [
                    months_control,
                    ft.ElevatedButton(
                        tr("common.save"),
                        icon=ft.Icons.CHECK,
                        height=input_h,
                        on_click=apply_projection_months,
                        style=primary_button_style(),
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
                tr("dash.projected_income", months=months),
                format_brl(income_total),
                tr("dash.avg_month", value=format_brl(detail.get("average_monthly_income", 0))),
                ft.Icons.TRENDING_UP,
                c.income,
            ),
            build_projection_metric_card(
                tr("dash.projected_expense", months=months),
                format_brl(expense_total),
                tr("dash.avg_month", value=format_brl(detail.get("average_monthly_expense", 0))),
                ft.Icons.TRENDING_DOWN,
                c.expense,
            ),
            build_projection_metric_card(
                tr("dash.projected_net", months=months),
                format_brl(net_total),
                tr("dash.net_formula"),
                ft.Icons.SHOW_CHART,
                c.accent_portfolio if net_total >= 0 else c.danger,
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
                tr("dash.projection_chart", months=months),
                projection_forecast_chart(detail.get("monthly_points", [])),
                height=chart_height,
                scroll_content=False,
                expand=True,
            ),
        ],
        spacing=4,
    )


def build_insight_card(view, current: dict, projection_detail: dict) -> ft.Container:
    c = theme_colors()
    net = current["net_savings"]
    rate = current["savings_rate"]

    if net > 0 and rate >= 20:
        message = tr("dash.insight_good")
        color = c.success
    elif net > 0:
        message = tr("dash.insight_ok")
        color = c.accent
    else:
        message = tr("dash.insight_bad")
        color = c.danger

    if projection_detail.get("has_history"):
        horizon = projection_detail.get("months_ahead", 3)
        message += (
            f" {tr('dash.projection_title')} {horizon}: "
            f"{format_brl(projection_detail.get('projected_income_total', 0))}, "
            f"{format_brl(projection_detail.get('projected_expense_total', 0))}, "
            f"{format_brl(projection_detail.get('projected_net_total', 0))}."
        )

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LIGHTBULB_OUTLINED, color=color, size=28),
                ft.Column(
                    [
                        ft.Text(tr("dash.period_read"), size=13, color=c.text_muted),
                        ft.Text(message, size=13, color=c.text_primary),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=16,
        ),
        padding=20,
        bgcolor=c.surface,
        border_radius=16,
        border=ft.Border.all(1, c.border),
    )


def build_due_dates_section(view) -> ft.Control:
    c = theme_colors()
    items = get_upcoming_due_dates(
        view.app.get_view_profile_id(),
        view.app.is_consolidated,
    )
    if not items:
        return section_card(
            tr("dash.due_title"),
            _compact_empty(
                icon=ft.Icons.EVENT_AVAILABLE,
                message=tr("dash.due_empty"),
            ),
        )
    rows = []
    kind_icon = {"card": ft.Icons.CREDIT_CARD, "das": ft.Icons.FACT_CHECK, "recurring": ft.Icons.REPEAT}
    from core.domain.locale_format import format_display_month_day

    for item in items:
        amt = f" • {format_brl(item['amount'])}" if item.get("amount") else ""
        rows.append(
            ft.Row(
                [
                    ft.Icon(kind_icon.get(item["kind"], ft.Icons.EVENT), color=c.accent, size=18),
                    ft.Text(format_display_month_day(item["date"]), size=12, color=c.text_muted, width=48),
                    ft.Text(f"{item['label']}{amt}", size=12, color=c.text_primary, expand=True),
                ],
                spacing=8,
            )
        )
    return section_card(tr("dash.due_title"), ft.Column(rows, spacing=6))


_ACTION_ROUTES = {
    "transactions": (1, False),
    "investments": (3, False),
    "reports": (4, False),
    "budgets": (5, False),
    "mei_home": (0, True),
    "mei_vendas": (1, True),
    "mei_obrigacoes": (2, True),
}


def run_dashboard_action(app, action: str | None) -> None:
    """Navigate from a dashboard CTA/decision to the matching personal or MEI tab."""
    from ui.router import switch_view

    if not action:
        return
    route = _ACTION_ROUTES.get(action)
    if not route:
        switch_view(app, 5)
        return
    index, mei = route
    if mei and app.is_mei_mode():
        app.switch_mei_tab(index)
    else:
        switch_view(app, index)


# Backward-compatible alias used inside this module.
_run_card_action = run_dashboard_action


def _decision_card_row(view, card: dict) -> ft.Control:
    c = theme_colors()
    color = status_color(severity=card.get("severity", "info"))
    hint = card.get("hint") or ""
    action = card.get("action")
    key = card.get("key", "")

    def dismiss(_):
        dismiss_insight(view.app.get_view_profile_id(), key)
        view.app.refresh_current_view()

    buttons = []
    if action:
        buttons.append(
            ft.TextButton(
                card.get("action_label") or tr("dash.action_view"),
                on_click=lambda _: _run_card_action(view.app, action),
                style=on_surface_button_style(),
            )
        )
    buttons.append(
        ft.IconButton(
            ft.Icons.CLOSE,
            icon_size=18,
            icon_color=c.text_muted,
            tooltip=tr("dash.dismiss"),
            style=ft.ButtonStyle(padding=12),
            on_click=dismiss,
        )
    )
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(card["message"], size=13, color=c.text_primary),
                ft.Text(hint, size=12, color=c.text_muted) if hint else ft.Container(),
                ft.Row(buttons, spacing=4),
            ],
            spacing=4,
            tight=True,
        ),
        padding=14,
        border=ft.Border.all(1, color),
        border_radius=12,
        bgcolor=c.surface_alt,
    )


# Top-of-fold decisions: scannable list (single source — no hub duplicate).
_DECISIONS_VISIBLE = 5


def build_decisions_section(view) -> ft.Control:
    cards = get_decision_cards(
        profile_id=view.app.get_view_profile_id(),
        consolidated=view.app.is_consolidated,
        year=view.data.get("period_year"),
        month=view.data.get("period_month") or date.today().month,
        limit=_DECISIONS_VISIBLE,
        include_dismissed=False,
    )
    if not cards:
        return section_card(
            tr("dash.decisions_title"),
            _compact_empty(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                message=tr("dash.decisions_empty"),
                action_label=tr("dash.see_transactions"),
                on_action=lambda: _run_card_action(view.app, "transactions"),
            ),
        )
    rows = [_decision_card_row(view, card) for card in cards]
    return section_card(tr("dash.decisions_title"), ft.Column(rows, spacing=8))


def build_local_insights_section(view) -> ft.Control:
    tips = get_local_finance_insights(
        profile_id=view.app.get_view_profile_id(),
        consolidated=view.app.is_consolidated,
        year=view.data.get("period_year"),
        month=view.data.get("period_month") or date.today().month,
    )
    rows = [ft.Text(tip, size=12, color=theme_colors().text_secondary) for tip in tips]
    return section_card(tr("dash.local_insights"), ft.Column(rows, spacing=6))


def build_budget_section(view, budgets: list, budget_month: int, period_year: int) -> ft.Control:
    """Orçamentos do mês com empty state + CTA."""
    title = tr(
        "dash.budgets_title",
        month=f"{budget_month:02d}",
        year=period_year,
    )
    if budgets:
        from ui.personal.charts import budget_status_chart

        return section_card(title, budget_status_chart(budgets), expand=True, height=300)

    return section_card(
        title,
        _compact_empty(
            icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
            message=tr("dash.budgets_empty"),
            action_label=tr("dash.configure_budgets"),
            on_action=lambda: _run_card_action(view.app, "budgets"),
        ),
        expand=True,
        height=300,
    )


def build_net_worth_section(view) -> ft.Control:
    c = theme_colors()
    if view.app.is_consolidated:
        return ft.Container()

    profile_id = view.app.get_view_profile_id()
    if not profile_id:
        return ft.Container()

    totals = get_net_worth_totals(profile_id)
    evolution = get_net_worth_evolution(profile_id)
    portfolio_value = totals.get("portfolio_value", Decimal("0"))
    if totals["total_assets"] == 0 and totals["total_liabilities"] == 0:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=c.accent, size=20),
                    ft.Text(
                        tr("dash.nw_hint"),
                        size=12,
                        color=c.text_muted,
                        expand=True,
                    ),
                    ft.TextButton(
                        tr("dash.open_settings"),
                        on_click=lambda _: _run_card_action(view.app, "budgets"),
                        style=on_surface_button_style(),
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            bgcolor=c.surface,
            border_radius=12,
            border=ft.Border.all(1, c.border),
        )

    metrics = [
        mini_patrimony(tr("dash.assets"), format_brl(totals["total_assets"]), c.success),
        mini_patrimony(tr("dash.liabilities"), format_brl(totals["total_liabilities"]), c.danger),
        mini_patrimony(tr("dash.net_worth"), format_brl(totals["net_worth"]), c.accent),
    ]
    if portfolio_value > 0:
        metrics.insert(1, mini_patrimony(tr("dash.portfolio_label"), format_brl(portfolio_value), c.accent_portfolio))

    return section_card(
        tr("dash.net_worth_title"),
        ft.Column(
            [
                ft.Row(metrics, spacing=24, wrap=True),
                net_worth_evolution_chart(evolution),
            ],
            spacing=12,
        ),
        height=220,
    )


def build_portfolio_section(view) -> ft.Control:
    c = theme_colors()
    if view.app.is_consolidated:
        return ft.Container()

    profile_id = view.app.get_view_profile_id()
    if not profile_id:
        return ft.Container()

    summary = get_portfolio_summary(profile_id, settings=view.app.settings)
    if not summary["holdings"]:
        return section_card(
            tr("dash.portfolio_title"),
            _compact_empty(
                icon=ft.Icons.SHOW_CHART,
                message=tr("dash.portfolio_empty"),
                action_label=tr("dash.portfolio_add"),
                on_action=lambda: _run_card_action(view.app, "investments"),
            ),
        )

    totals = summary["totals"]
    allocation = summary.get("allocation") or []
    cost = totals["cost_basis"]
    pnl = totals["pnl"]
    pnl_pct = float((pnl / cost) * 100) if cost > 0 else 0.0
    pnl_color = status_color(positive=pnl >= 0)

    def open_investments(_):
        _run_card_action(view.app, "investments")

    allocation_chart = (
        horizontal_bar_chart(allocation, label_key="label", value_key="value", max_items=5)
        if allocation
        else ft.Container()
    )

    return section_card(
        tr("dash.portfolio_title"),
        ft.Column(
            [
                ft.Row(
                    [
                        mini_patrimony(tr("dash.portfolio_market"), format_brl(totals["market_value"]), c.accent_portfolio),
                        mini_patrimony(tr("dash.portfolio_cost"), format_brl(cost), c.text_secondary),
                        mini_patrimony(
                            tr("dash.portfolio_result"),
                            f"{format_brl(pnl)} · {signed_label(pnl_pct)}",
                            pnl_color,
                        ),
                    ],
                    spacing=24,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                allocation_chart,
                ft.Row(
                    [
                        ft.Container(expand=True),
                        ft.TextButton(
                            tr("dash.portfolio_see"),
                            on_click=open_investments,
                            style=on_surface_button_style(),
                        ),
                    ],
                ),
            ],
            spacing=12,
            tight=True,
        ),
        scroll_content=False,
    )


def build_goals_section(view) -> ft.Container:
    c = theme_colors()
    goals = get_active_goals()

    if not goals:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FLAG_OUTLINED, color=c.accent, size=20),
                    ft.Text(
                        tr("dash.goals_empty"),
                        size=12,
                        color=c.text_muted,
                        expand=True,
                    ),
                    ft.TextButton(
                        tr("dash.goals_create"),
                        on_click=lambda _: _run_card_action(view.app, "budgets"),
                        style=on_surface_button_style(),
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            bgcolor=c.surface,
            border_radius=12,
            border=ft.Border.all(1, c.border),
        )

    goal_cards = []
    for goal in goals[:3]:
        current = Decimal(str(goal.get("current_amount", 0)))
        target = Decimal(str(goal.get("target_amount", 1)))
        pct = min(float((current / target) * 100), 100) if target > 0 else 0
        if pct >= 100:
            progress_color = c.success
        elif pct > 60:
            progress_color = c.accent
        else:
            progress_color = c.expense

        goal_cards.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(goal["name"], size=12, weight=ft.FontWeight.W_600, expand=True),
                                ft.Text(f"{pct:.0f}%", size=12, color=progress_color, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        ft.ProgressBar(value=pct / 100, color=progress_color, bgcolor=c.border, height=6),
                        ft.Row(
                            [
                                ft.Text(format_brl(current), size=12, color=c.text_muted),
                                ft.Text(tr("dash.goal_target", amount=format_brl(target)), size=12, color=c.text_muted),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=4,
                ),
                padding=12,
                bgcolor=c.surface_alt,
                border_radius=10,
                expand=True,
            )
        )

    header_trailing: list[ft.Control] = [
        ft.Icon(ft.Icons.FLAG_OUTLINED, color=c.accent, size=18),
        ft.Text(
            tr("dash.goals_title"),
            size=13,
            weight=ft.FontWeight.W_600,
            color=c.text_primary,
            expand=True,
        ),
    ]
    if len(goals) > 3:
        header_trailing.append(
            ft.TextButton(
                tr("dash.goals_see_all", count=len(goals)),
                on_click=lambda _: _run_card_action(view.app, "budgets"),
                style=on_surface_button_style(),
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(header_trailing, spacing=8),
                ft.Row(goal_cards, spacing=12),
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor=c.surface,
        border_radius=12,
        border=ft.Border.all(1, c.border),
    )
