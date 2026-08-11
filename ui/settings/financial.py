"""Categories, budgets, and financial defaults."""

from __future__ import annotations

import flet as ft

from datetime import date
from decimal import Decimal
from core.db.repositories.budgets import delete_budget, get_budgets_for_month, set_budget
from core.db.repositories.goals import create_goal, delete_goal, get_active_goals, update_goal_progress
from core.db.repositories.net_worth import (
    create_asset, create_liability, delete_asset, delete_liability,
    get_assets, get_liabilities, get_net_worth_totals,
)
from core.engine.categorization import (
    apply_rules_retroactive,
    create_rule,
    delete_rule,
    get_all_rules,
    update_rule,
)
from core.models import TransactionType, Asset, Liability
from ui.personal.period_filter import month_options

from core.i18n import t
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *


def build_goals_section(ctx: SettingsCtx) -> ft.Container:
    goals = get_active_goals(ctx.app.get_view_profile_id() if not ctx.app.is_consolidated else None)

    def add_goal(e):
        name_field = _modal_field(label=t("settings.goal_name"))
        target_field = _modal_field(label=t("settings.goal_target"), keyboard_type=ft.KeyboardType.NUMBER)
        deadline_field = _modal_field(label=t("settings.goal_deadline"), hint_text=t("common.optional"))
        profile_dropdown = _modal_dropdown(
            label=t("settings.goal_profile"),
            options=[ft.dropdown.Option("", t("settings.goal_all_profiles"))]
            + [ft.dropdown.Option(str(p.id), p.name) for p in ctx.profiles],
            value=str(ctx.app.get_view_profile_id() or ""),
        )

        def save(ev):
            name = (name_field.value or "").strip()
            if not name:
                ctx.app.show_snack(t("settings.goal_need_name"), success=False)
                return
            try:
                target = float((target_field.value or "0").replace(",", "."))
                if target <= 0:
                    raise ValueError(t("settings.goal_invalid_value"))
                deadline = None
                if deadline_field.value:
                    from datetime import datetime as dt
                    deadline = dt.strptime(deadline_field.value.strip(), "%Y-%m-%d").date()
                profile_id = int(profile_dropdown.value) if profile_dropdown.value else None
                create_goal(name, target, deadline, profile_id)
            except Exception as ex:
                ctx.app.show_snack(t("settings.goal_create_error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.goal_created"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    target_field,
                    deadline_field,
                    profile_dropdown,
                    profile_modal_actions(ctx.app, t("settings.goal_create"), save),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.goal_new_title"),
        )

    def add_progress(goal_id: int):
        amount_field = _modal_field(label=t("settings.goal_add_amount"), keyboard_type=ft.KeyboardType.NUMBER)

        def save(ev):
            try:
                amount = float((amount_field.value or "0").replace(",", "."))
                if amount <= 0:
                    raise ValueError(t("settings.goal_invalid_value"))
                update_goal_progress(goal_id, amount)
            except Exception as ex:
                ctx.app.show_snack(t("common.error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.goal_progress_updated"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [amount_field, profile_modal_actions(ctx.app, t("common.add"), save)],
                spacing=12,
                tight=True,
            ),
            title=t("settings.goal_progress_title"),
        )

    def remove_goal(goal_id: int):
        def confirm(ev):
            if delete_goal(goal_id):
                ctx.app.close_modal()
                ctx.app.show_snack(t("settings.goal_removed"))
                ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    _modal_text(t("settings.goal_remove_q")),
                    ft.Row(
                        [
                            ft.TextButton(
                                t("common.cancel"),
                                on_click=lambda _: ctx.app.close_modal(),
                                style=on_surface_button_style(),
                            ),
                            _danger_button(t("common.delete"), confirm),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("common.confirm"),
        )

    goal_list = ft.Column(spacing=8)
    for g in goals:
        current = float(g.get("current_amount") or 0)
        target = float(g.get("target_amount") or 1)
        pct = min((current / target) * 100, 100) if target else 0
        goal_list.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(g["name"], size=14, color=theme_colors().text_primary, weight=ft.FontWeight.W_600),
                                ft.Text(
                                    f"R$ {current:,.2f} / R$ {target:,.2f} ({pct:.0f}%)",
                                    size=11,
                                    color=theme_colors().text_muted,
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.IconButton(
                            ft.Icons.ADD_CIRCLE_OUTLINE,
                            icon_size=18,
                            tooltip=t("settings.goal_progress_tip"),
                            on_click=lambda e, gid=g["id"]: add_progress(gid),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            tooltip=t("settings.goal_remove_tip"),
                            on_click=lambda e, gid=g["id"]: remove_goal(gid),
                        ),
                    ],
                    spacing=8,
                ),
                padding=12,
                bgcolor=theme_colors().surface_alt,
                border_radius=10,
            )
        )

    if not goal_list.controls:
        goal_list.controls.append(
            ft.Text(
                t("settings.goals_empty"),
                color=theme_colors().text_muted,
                size=13,
            )
        )

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            t("settings.goals_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme_colors().text_primary,
                        ),
                        ft.ElevatedButton(
                            t("settings.goals_new"),
                            icon=ft.Icons.FLAG,
                            on_click=add_goal,
                            style=primary_button_style(),
                            icon_color=theme_colors().on_accent,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                goal_list,
            ],
            spacing=12,
        ),
    )

def build_net_worth_section(ctx: SettingsCtx) -> ft.Container:
    profile_id = ctx.app.get_view_profile_id()
    if not profile_id:
        return section_card(
            ft.Text(
                t("settings.nw_select_profile"),
                color=theme_colors().text_muted,
                size=13,
            ),
        )

    assets = get_assets(profile_id)
    liabilities = get_liabilities(profile_id)
    totals = get_net_worth_totals(profile_id)

    def add_asset(_):
        name_f = _modal_field(label=t("settings.nw_asset_name"), width=320)
        value_f = _modal_field(label=t("settings.nw_asset_value"), width=320, keyboard_type=ft.KeyboardType.NUMBER)
        type_dd = _modal_dropdown(
            label=t("common.type"),
            width=320,
            value="other",
            options=[
                ft.dropdown.Option("cash", t("settings.nw_type_cash")),
                ft.dropdown.Option("investment", t("settings.nw_type_investment")),
                ft.dropdown.Option("property", t("settings.nw_type_property")),
                ft.dropdown.Option("vehicle", t("settings.nw_type_vehicle")),
                ft.dropdown.Option("other", t("settings.nw_type_other")),
            ],
        )

        def save(ev):
            try:
                val = Decimal((value_f.value or "0").replace(",", "."))
                create_asset(Asset(profile_id=profile_id, name=name_f.value or t("settings.nw_asset_default"), asset_type=type_dd.value or "other", current_value=val))
            except Exception as ex:
                ctx.app.show_snack(t("common.error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.nw_asset_saved"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column([name_f, value_f, type_dd, _action_button(t("common.save"), save)], spacing=12, tight=True),
            title=t("settings.nw_asset_new"),
        )

    def add_liability(_):
        name_f = _modal_field(label=t("settings.nw_liability_name"), width=320)
        value_f = _modal_field(label=t("settings.nw_liability_value"), width=320, keyboard_type=ft.KeyboardType.NUMBER)
        type_dd = _modal_dropdown(
            label=t("common.type"),
            width=320,
            value="other",
            options=[
                ft.dropdown.Option("loan", t("settings.nw_type_loan")),
                ft.dropdown.Option("credit_card", t("settings.nw_type_credit_card")),
                ft.dropdown.Option("mortgage", t("settings.nw_type_mortgage")),
                ft.dropdown.Option("other", t("settings.nw_type_other")),
            ],
        )

        def save(ev):
            try:
                val = Decimal((value_f.value or "0").replace(",", "."))
                create_liability(Liability(profile_id=profile_id, name=name_f.value or t("settings.nw_liability_default"), liability_type=type_dd.value or "other", current_balance=val))
            except Exception as ex:
                ctx.app.show_snack(t("common.error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.nw_liability_saved"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column([name_f, value_f, type_dd, _action_button(t("common.save"), save)], spacing=12, tight=True),
            title=t("settings.nw_liability_new"),
        )

    asset_rows = [
        ft.ListTile(
            title=ft.Text(a.name, color=theme_colors().text_primary, size=13),
            subtitle=ft.Text(f"R$ {float(a.current_value):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=theme_colors().text_muted, size=11),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=theme_colors().danger, on_click=lambda e, aid=a.id: delete_asset(aid)),
        )
        for a in assets
    ] or [ft.Text(t("settings.nw_asset_none"), color=theme_colors().text_muted, size=12)]

    liability_rows = [
        ft.ListTile(
            title=ft.Text(l.name, color=theme_colors().text_primary, size=13),
            subtitle=ft.Text(f"R$ {float(l.current_balance):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=theme_colors().text_muted, size=11),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=theme_colors().danger, on_click=lambda e, lid=l.id: delete_liability(lid)),
        )
        for l in liabilities
    ] or [ft.Text(t("settings.nw_liability_none"), color=theme_colors().text_muted, size=12)]

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            t("settings.nw_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme_colors().text_primary,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            t("settings.nw_net", value=f"R$ {float(totals['net_worth']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                            size=13,
                            color=_ACCENT,
                        ),
                    ],
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(t("settings.nw_asset_new"), icon=ft.Icons.ADD, on_click=add_asset),
                        ft.ElevatedButton(t("settings.nw_liability_new"), icon=ft.Icons.REMOVE, on_click=add_liability),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        ft.Container(content=ft.Column(asset_rows, spacing=0), expand=True, padding=12, bgcolor=theme_colors().surface_alt, border_radius=8),
                        ft.Container(content=ft.Column(liability_rows, spacing=0), expand=True, padding=12, bgcolor=theme_colors().surface_alt, border_radius=8),
                    ],
                    spacing=12,
                ),
            ],
            spacing=12,
        ),
    )

def delete_asset(ctx: SettingsCtx, asset_id: int):
    delete_asset(asset_id)
    ctx.app.show_snack(t("settings.nw_asset_removed"))
    ctx.app.refresh_current_view()

def delete_liability(ctx: SettingsCtx, liability_id: int):
    delete_liability(liability_id)
    ctx.app.show_snack(t("settings.nw_liability_removed"))
    ctx.app.refresh_current_view()

def build_budgets_section(ctx: SettingsCtx) -> ft.Container:
    from datetime import date
    from ui.personal.period_filter import month_options

    today = date.today()
    budget_year = ctx.app.filter_year or today.year
    budget_month = ctx.app.filter_month or today.month
    profile_id = ctx.app.get_view_profile_id()

    expense_cats = [c for c in ctx.categories if c.type == TransactionType.EXPENSE]
    budgets = get_budgets_for_month(budget_year, budget_month, profile_id) if profile_id else []

    def add_budget(_):
        if not profile_id:
            ctx.app.show_snack(t("settings.budget_need_profile"), success=False)
            return

        cat_dropdown = _modal_dropdown(
            label=t("settings.budget_cat"),
            width=360,
            options=[
                ft.dropdown.Option(
                    str(c.id),
                    f"{c.icon} {__import__('core.db.repositories.categories', fromlist=['display_name']).display_name(c)}",
                )
                for c in expense_cats
            ],
        )
        limit_field = _modal_field(label=t("settings.budget_limit"), width=360, keyboard_type=ft.KeyboardType.NUMBER)
        year_field = _modal_field(label=t("common.year"), value=str(budget_year), width=160)
        month_dropdown = _modal_dropdown(
            label=t("common.month"),
            width=200,
            value=str(budget_month),
            options=[ft.dropdown.Option(key, label) for key, label in month_options() if key != "0"],
        )

        def save(ev):
            if not cat_dropdown.value:
                ctx.app.show_snack(t("settings.budget_need_cat"), success=False)
                return
            try:
                limit_val = float((limit_field.value or "0").replace(",", "."))
                year_val = int(year_field.value)
                month_val = int(month_dropdown.value)
                if limit_val <= 0:
                    raise ValueError(t("settings.budget_invalid"))
                set_budget(profile_id, int(cat_dropdown.value), year_val, month_val, limit_val)
            except Exception as ex:
                ctx.app.show_snack(t("common.error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.budget_saved"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    cat_dropdown,
                    limit_field,
                    ft.Row([year_field, month_dropdown], spacing=12),
                    profile_modal_actions(ctx.app, t("common.save"), save),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.budget_new_title"),
        )

    def remove_budget(budget_id: int):
        delete_budget(budget_id)
        ctx.app.show_snack(t("settings.budget_removed"))
        ctx.app.refresh_current_view()

    budget_list = ft.Column(spacing=8)
    for b in budgets:
        status_color = theme_colors().success if b["status"] == "ok" else (theme_colors().warning if b["status"] == "warning" else theme_colors().danger)
        budget_list.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    f"{b.get('icon', '')} {b['category_name']}",
                                    size=13,
                                    color=theme_colors().text_primary,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    f"{budget_month:02d}/{budget_year} • "
                                    f"R$ {float(b['spent']):,.2f} / R$ {float(b['limit']):,.2f} ({b['percentage']:.0f}%)",
                                    size=11,
                                    color=status_color,
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            tooltip=t("settings.budget_remove_tip"),
                            on_click=lambda e, bid=b["id"]: remove_budget(bid),
                        ),
                    ],
                    spacing=8,
                ),
                padding=12,
                bgcolor=theme_colors().surface_alt,
                border_radius=10,
            )
        )

    if not profile_id:
        hint = ft.Text(
            t("settings.budget_profile_hint"),
            color=theme_colors().text_muted,
            size=12,
        )
    elif not budget_list.controls:
        hint = ft.Text(t("settings.budget_empty_period"), color=theme_colors().text_muted, size=13)
    else:
        hint = ft.Container()

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            t("settings.budgets_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme_colors().text_primary,
                        ),
                        ft.ElevatedButton(
                            t("settings.budgets_new"),
                            icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                            on_click=add_budget,
                            style=primary_button_style(),
                            icon_color=theme_colors().on_accent,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    t("settings.budget_period", month=f"{budget_month:02d}", year=budget_year),
                    size=11,
                    color=theme_colors().text_muted,
                ),
                hint,
                budget_list,
            ],
            spacing=12,
        ),
    )

def build_rules_section(ctx: SettingsCtx) -> ft.Container:
    rules = get_all_rules()
    cat_map = {c.id: c for c in ctx.categories}

    def edit_rule(rule):
        pattern_field = _modal_field(label=t("settings.rule_pattern"), value=rule.pattern)
        match_dropdown = _modal_dropdown(
            label=t("settings.rule_match"),
            options=[
                ft.dropdown.Option("contains", t("settings.rule_contains")),
                ft.dropdown.Option("starts_with", t("settings.rule_starts")),
                ft.dropdown.Option("equals", t("settings.rule_equals")),
            ],
            value=rule.match_type,
        )
        cat_dropdown = _modal_dropdown(
            label=t("settings.rule_assign"),
            options=[
                ft.dropdown.Option(
                    str(c.id),
                    f"{c.icon or ''} {__import__('core.db.repositories.categories', fromlist=['display_name']).display_name(c)}",
                )
                for c in ctx.categories
            ],
            value=str(rule.category_id),
        )

        def save(ev):
            pattern = (pattern_field.value or "").strip()
            if not pattern or not cat_dropdown.value:
                ctx.app.show_snack(t("settings.rule_need_fields"), success=False)
                return
            update_rule(
                rule.id,
                pattern=pattern,
                category_id=int(cat_dropdown.value),
                match_type=match_dropdown.value,
            )
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.rule_updated"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [pattern_field, match_dropdown, cat_dropdown, profile_modal_actions(ctx.app, t("common.save"), save)],
                spacing=12,
                tight=True,
            ),
            title=t("settings.rule_edit_title"),
        )

    def add_rule(e):
        pattern_field = _modal_field(label=t("settings.rule_pattern"), hint_text="IFOOD")
        match_dropdown = _modal_dropdown(
            label=t("settings.rule_match"),
            options=[
                ft.dropdown.Option("contains", t("settings.rule_contains")),
                ft.dropdown.Option("starts_with", t("settings.rule_starts")),
                ft.dropdown.Option("equals", t("settings.rule_equals")),
            ],
            value="contains",
        )
        cat_dropdown = _modal_dropdown(
            label=t("settings.rule_assign"),
            options=[
                ft.dropdown.Option(
                    str(c.id),
                    f"{c.icon or ''} {__import__('core.db.repositories.categories', fromlist=['display_name']).display_name(c)}",
                )
                for c in ctx.categories
            ],
            value=str(ctx.categories[0].id) if ctx.categories else None,
        )

        def save(ev):
            pattern = (pattern_field.value or "").strip()
            if not pattern or not cat_dropdown.value:
                ctx.app.show_snack(t("settings.rule_need_fields"), success=False)
                return
            create_rule(pattern, int(cat_dropdown.value), match_dropdown.value)
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.rule_created"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [pattern_field, match_dropdown, cat_dropdown, profile_modal_actions(ctx.app, t("settings.rule_save"), save)],
                spacing=12,
                tight=True,
            ),
            title=t("settings.rule_new_title"),
        )

    def retroactive(e):
        n = apply_rules_retroactive(ctx.app.get_view_profile_id())
        ctx.app.show_snack(t("settings.rule_retro", count=n))

    from core.db.repositories.categories import display_name

    rule_list = ft.Column(spacing=6)
    for r in rules:
        cat = cat_map.get(r.category_id)
        cat_label = display_name(cat) if cat else r.category_id
        label = f"{r.match_type}: '{r.pattern}' → {cat_label}"
        rule_list.controls.append(
            ft.Row(
                [
                    ft.Text(label, expand=True, size=12, color=theme_colors().text_primary),
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_size=16,
                        on_click=lambda e, rule=r: edit_rule(rule),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        on_click=lambda e, rid=r.id: remove_rule(ctx, rid),
                    ),
                ]
            )
        )
    if not rule_list.controls:
        rule_list.controls.append(ft.Text(t("settings.rules_empty"), color=theme_colors().text_muted, size=12))

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(t("settings.rules_title"), size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(t("settings.rules_new"), on_click=add_rule, style=primary_button_style()),
                        ft.OutlinedButton(t("settings.rules_apply"), on_click=retroactive, style=on_surface_button_style()),
                    ],
                    spacing=8,
                ),
                rule_list,
            ],
            spacing=12,
        ),
    )

def remove_rule(ctx: SettingsCtx, rule_id: int):
    if delete_rule(rule_id):
        ctx.app.show_snack(t("settings.rule_removed"))
        ctx.app.refresh_current_view()
