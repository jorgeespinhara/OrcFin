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
from ui.personal.period_filter import MONTH_OPTIONS

from ui.settings.context import SettingsCtx
from ui.settings.helpers import *


def build_goals_section(ctx: SettingsCtx) -> ft.Container:
    goals = get_active_goals(ctx.app.get_view_profile_id() if not ctx.app.is_consolidated else None)

    def add_goal(e):
        name_field = _modal_field(label="Nome da meta")
        target_field = _modal_field(label="Valor alvo (R$)", keyboard_type=ft.KeyboardType.NUMBER)
        deadline_field = _modal_field(label="Prazo (AAAA-MM-DD)", hint_text="Opcional")
        profile_dropdown = _modal_dropdown(
            label="Perfil (opcional)",
            options=[ft.dropdown.Option("", "Todos / família")]
            + [ft.dropdown.Option(str(p.id), p.name) for p in ctx.profiles],
            value=str(ctx.app.get_view_profile_id() or ""),
        )

        def save(ev):
            name = (name_field.value or "").strip()
            if not name:
                ctx.app.show_snack("Informe o nome da meta", success=False)
                return
            try:
                target = float((target_field.value or "0").replace(",", "."))
                if target <= 0:
                    raise ValueError("Valor inválido")
                deadline = None
                if deadline_field.value:
                    from datetime import datetime as dt
                    deadline = dt.strptime(deadline_field.value.strip(), "%Y-%m-%d").date()
                profile_id = int(profile_dropdown.value) if profile_dropdown.value else None
                create_goal(name, target, deadline, profile_id)
            except Exception as ex:
                ctx.app.show_snack(f"Erro ao criar meta: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Meta criada!")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    target_field,
                    deadline_field,
                    profile_dropdown,
                    profile_modal_actions(ctx.app, "Criar Meta", save),
                ],
                spacing=12,
                tight=True,
            ),
            title="Nova Meta Financeira",
        )

    def add_progress(goal_id: int):
        amount_field = _modal_field(label="Valor a adicionar (R$)", keyboard_type=ft.KeyboardType.NUMBER)

        def save(ev):
            try:
                amount = float((amount_field.value or "0").replace(",", "."))
                if amount <= 0:
                    raise ValueError("Valor inválido")
                update_goal_progress(goal_id, amount)
            except Exception as ex:
                ctx.app.show_snack(f"Erro: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Progresso atualizado!")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [amount_field, profile_modal_actions(ctx.app, "Adicionar", save)],
                spacing=12,
                tight=True,
            ),
            title="Atualizar Progresso",
        )

    def remove_goal(goal_id: int):
        def confirm(ev):
            if delete_goal(goal_id):
                ctx.app.close_modal()
                ctx.app.show_snack("Meta removida")
                ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    _modal_text("Remover esta meta?"),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Cancelar",
                                on_click=lambda _: ctx.app.close_modal(),
                                style=on_surface_button_style(),
                            ),
                            _action_button("Remover", confirm, bgcolor="#EF4444"),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title="Confirmar",
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
                            tooltip="Adicionar progresso",
                            on_click=lambda e, gid=g["id"]: add_progress(gid),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            tooltip="Remover meta",
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
            ft.Text("Nenhuma meta ativa.", color=theme_colors().text_muted, size=13)
        )

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Metas Financeiras", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            "Nova Meta",
                            icon=ft.Icons.FLAG,
                            on_click=add_goal,
                            style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                            icon_color=ft.Colors.WHITE,
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
                "Patrimônio: selecione um perfil individual para cadastrar ativos e passivos.",
                color=theme_colors().text_muted,
                size=13,
            ),
        )

    assets = get_assets(profile_id)
    liabilities = get_liabilities(profile_id)
    totals = get_net_worth_totals(profile_id)

    def add_asset(_):
        name_f = _modal_field(label="Nome do ativo", width=320)
        value_f = _modal_field(label="Valor atual (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER)
        type_dd = _modal_dropdown(
            label="Tipo",
            width=320,
            value="other",
            options=[
                ft.dropdown.Option("cash", "Dinheiro / conta"),
                ft.dropdown.Option("investment", "Investimentos"),
                ft.dropdown.Option("property", "Imóvel"),
                ft.dropdown.Option("vehicle", "Veículo"),
                ft.dropdown.Option("other", "Outro"),
            ],
        )

        def save(ev):
            try:
                val = Decimal((value_f.value or "0").replace(",", "."))
                create_asset(Asset(profile_id=profile_id, name=name_f.value or "Ativo", asset_type=type_dd.value or "other", current_value=val))
            except Exception as ex:
                ctx.app.show_snack(f"Erro: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Ativo cadastrado")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column([name_f, value_f, type_dd, _action_button("Salvar", save)], spacing=12, tight=True),
            title="Novo ativo",
        )

    def add_liability(_):
        name_f = _modal_field(label="Nome do passivo", width=320)
        value_f = _modal_field(label="Saldo atual (R$)", width=320, keyboard_type=ft.KeyboardType.NUMBER)
        type_dd = _modal_dropdown(
            label="Tipo",
            width=320,
            value="other",
            options=[
                ft.dropdown.Option("loan", "Empréstimo"),
                ft.dropdown.Option("credit_card", "Cartão de crédito"),
                ft.dropdown.Option("mortgage", "Financiamento"),
                ft.dropdown.Option("other", "Outro"),
            ],
        )

        def save(ev):
            try:
                val = Decimal((value_f.value or "0").replace(",", "."))
                create_liability(Liability(profile_id=profile_id, name=name_f.value or "Passivo", liability_type=type_dd.value or "other", current_balance=val))
            except Exception as ex:
                ctx.app.show_snack(f"Erro: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Passivo cadastrado")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column([name_f, value_f, type_dd, _action_button("Salvar", save)], spacing=12, tight=True),
            title="Novo passivo",
        )

    asset_rows = [
        ft.ListTile(
            title=ft.Text(a.name, color=theme_colors().text_primary, size=13),
            subtitle=ft.Text(f"R$ {float(a.current_value):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=theme_colors().text_muted, size=11),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#EF4444", on_click=lambda e, aid=a.id: delete_asset(aid)),
        )
        for a in assets
    ] or [ft.Text("Nenhum ativo", color=theme_colors().text_muted, size=12)]

    liability_rows = [
        ft.ListTile(
            title=ft.Text(l.name, color=theme_colors().text_primary, size=13),
            subtitle=ft.Text(f"R$ {float(l.current_balance):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=theme_colors().text_muted, size=11),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#EF4444", on_click=lambda e, lid=l.id: delete_liability(lid)),
        )
        for l in liabilities
    ] or [ft.Text("Nenhum passivo", color=theme_colors().text_muted, size=12)]

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Patrimônio Líquido", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.Container(expand=True),
                        ft.Text(
                            f"Líquido: R$ {float(totals['net_worth']):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            size=13,
                            color=_ACCENT,
                        ),
                    ],
                ),
                ft.Row(
                    [
                        ft.ElevatedButton("Novo ativo", icon=ft.Icons.ADD, on_click=add_asset),
                        ft.ElevatedButton("Novo passivo", icon=ft.Icons.REMOVE, on_click=add_liability),
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
    ctx.app.show_snack("Ativo removido")
    ctx.app.refresh_current_view()

def delete_liability(ctx: SettingsCtx, liability_id: int):
    delete_liability(liability_id)
    ctx.app.show_snack("Passivo removido")
    ctx.app.refresh_current_view()

def build_budgets_section(ctx: SettingsCtx) -> ft.Container:
    from datetime import date
    from ui.personal.period_filter import MONTH_OPTIONS

    today = date.today()
    budget_year = ctx.app.filter_year or today.year
    budget_month = ctx.app.filter_month or today.month
    profile_id = ctx.app.get_view_profile_id()

    expense_cats = [c for c in ctx.categories if c.type == TransactionType.EXPENSE]
    budgets = get_budgets_for_month(budget_year, budget_month, profile_id) if profile_id else []

    def add_budget(_):
        if not profile_id:
            ctx.app.show_snack("Selecione um perfil individual para definir orçamento", success=False)
            return

        cat_dropdown = _modal_dropdown(
            label="Categoria de despesa",
            width=360,
            options=[ft.dropdown.Option(str(c.id), f"{c.icon} {c.name}") for c in expense_cats],
        )
        limit_field = _modal_field(label="Limite mensal (R$)", width=360, keyboard_type=ft.KeyboardType.NUMBER)
        year_field = _modal_field(label="Ano", value=str(budget_year), width=160)
        month_dropdown = _modal_dropdown(
            label="Mês",
            width=200,
            value=str(budget_month),
            options=[ft.dropdown.Option(key, label) for key, label in MONTH_OPTIONS if key != "0"],
        )

        def save(ev):
            if not cat_dropdown.value:
                ctx.app.show_snack("Selecione uma categoria", success=False)
                return
            try:
                limit_val = float((limit_field.value or "0").replace(",", "."))
                year_val = int(year_field.value)
                month_val = int(month_dropdown.value)
                if limit_val <= 0:
                    raise ValueError("Limite inválido")
                set_budget(profile_id, int(cat_dropdown.value), year_val, month_val, limit_val)
            except Exception as ex:
                ctx.app.show_snack(f"Erro: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Orçamento salvo")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    cat_dropdown,
                    limit_field,
                    ft.Row([year_field, month_dropdown], spacing=12),
                    profile_modal_actions(ctx.app, "Salvar", save),
                ],
                spacing=12,
                tight=True,
            ),
            title="Novo Orçamento Mensal",
        )

    def remove_budget(budget_id: int):
        delete_budget(budget_id)
        ctx.app.show_snack("Orçamento removido")
        ctx.app.refresh_current_view()

    budget_list = ft.Column(spacing=8)
    for b in budgets:
        status_color = "#22C55E" if b["status"] == "ok" else ("#F59E0B" if b["status"] == "warning" else "#EF4444")
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
                            tooltip="Remover orçamento",
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
            "Orçamentos são por perfil individual. Mude para visão Individual no topo.",
            color=theme_colors().text_muted,
            size=12,
        )
    elif not budget_list.controls:
        hint = ft.Text("Nenhum orçamento para o período atual.", color=theme_colors().text_muted, size=13)
    else:
        hint = ft.Container()

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Orçamentos por Categoria", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            "Novo Orçamento",
                            icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                            on_click=add_budget,
                            style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                            icon_color=ft.Colors.WHITE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    f"Período: {budget_month:02d}/{budget_year} (usa o filtro global de ano/mês)",
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
        pattern_field = _modal_field(label="Se descrição contém...", value=rule.pattern)
        match_dropdown = _modal_dropdown(
            label="Condição",
            options=[
                ft.dropdown.Option("contains", "Contém"),
                ft.dropdown.Option("starts_with", "Começa com"),
                ft.dropdown.Option("equals", "Igual a"),
            ],
            value=rule.match_type,
        )
        cat_dropdown = _modal_dropdown(
            label="Atribuir categoria",
            options=[
                ft.dropdown.Option(str(c.id), f"{c.icon or ''} {c.name}")
                for c in ctx.categories
            ],
            value=str(rule.category_id),
        )

        def save(ev):
            pattern = (pattern_field.value or "").strip()
            if not pattern or not cat_dropdown.value:
                ctx.app.show_snack("Preencha padrão e categoria", success=False)
                return
            update_rule(
                rule.id,
                pattern=pattern,
                category_id=int(cat_dropdown.value),
                match_type=match_dropdown.value,
            )
            ctx.app.close_modal()
            ctx.app.show_snack("Regra atualizada")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [pattern_field, match_dropdown, cat_dropdown, profile_modal_actions(ctx.app, "Salvar", save)],
                spacing=12,
                tight=True,
            ),
            title="Editar regra",
        )

    def add_rule(e):
        pattern_field = _modal_field(label="Se descrição contém...", hint_text="IFOOD")
        match_dropdown = _modal_dropdown(
            label="Condição",
            options=[
                ft.dropdown.Option("contains", "Contém"),
                ft.dropdown.Option("starts_with", "Começa com"),
                ft.dropdown.Option("equals", "Igual a"),
            ],
            value="contains",
        )
        cat_dropdown = _modal_dropdown(
            label="Atribuir categoria",
            options=[
                ft.dropdown.Option(str(c.id), f"{c.icon or ''} {c.name}")
                for c in ctx.categories
            ],
            value=str(ctx.categories[0].id) if ctx.categories else None,
        )

        def save(ev):
            pattern = (pattern_field.value or "").strip()
            if not pattern or not cat_dropdown.value:
                ctx.app.show_snack("Preencha padrão e categoria", success=False)
                return
            create_rule(pattern, int(cat_dropdown.value), match_dropdown.value)
            ctx.app.close_modal()
            ctx.app.show_snack("Regra criada!")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [pattern_field, match_dropdown, cat_dropdown, profile_modal_actions(ctx.app, "Salvar Regra", save)],
                spacing=12,
                tight=True,
            ),
            title="Nova Regra de Categorização",
        )

    def retroactive(e):
        n = apply_rules_retroactive(ctx.app.get_view_profile_id())
        ctx.app.show_snack(f"{n} lançamentos recategorizados por regras")

    rule_list = ft.Column(spacing=6)
    for r in rules:
        cat = cat_map.get(r.category_id)
        label = f"{r.match_type}: '{r.pattern}' → {cat.name if cat else r.category_id}"
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
        rule_list.controls.append(ft.Text("Nenhuma regra. Ex: IFOOD → Alimentação", color=theme_colors().text_muted, size=12))

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Regras de Auto-categorização", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton("Nova Regra", on_click=add_rule, style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE)),
                        ft.OutlinedButton("Aplicar retroativo", on_click=retroactive, style=on_surface_button_style()),
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
        ctx.app.show_snack("Regra removida")
        ctx.app.refresh_current_view()
