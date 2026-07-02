"""Profile and bank account management."""

from __future__ import annotations

import flet as ft

from core.db.repositories.categories import create_category, delete_category
from core.db.repositories.profiles import create_profile, delete_profile as deactivate_profile, update_profile
from core.models import TransactionType

from ui.settings.context import SettingsCtx
from ui.settings.helpers import *


def build_profiles_section(ctx: SettingsCtx) -> ft.Container:
    def add_profile(e):
        name_field = _modal_field(label="Nome do Perfil", autofocus=True)
        color_field = _modal_field(label="Cor (hex)", value="#14B8A6")
        color_preview = ft.Container(width=24, height=24, bgcolor="#14B8A6", border_radius=12)

        def on_color_change(ev):
            color = (color_field.value or "#14B8A6").strip()
            if not color.startswith("#"):
                color = f"#{color}"
            color_preview.bgcolor = color
            color_preview.update()

        color_field.on_change = on_color_change

        color_swatches = ft.Row(
            [
                ft.Container(
                    width=28,
                    height=28,
                    bgcolor=color,
                    border_radius=14,
                    border=ft.Border.all(2, "#64748B"),
                    on_click=lambda _, c=color: (
                        setattr(color_field, "value", c),
                        setattr(color_preview, "bgcolor", c),
                        color_field.update(),
                        color_preview.update(),
                    ),
                )
                for color in PROFILE_COLORS
            ],
            spacing=8,
            wrap=True,
        )

        def save(ev):
            name = (name_field.value or "").strip()
            if not name:
                ctx.app.show_snack("Informe o nome do perfil", success=False)
                return
            color = (color_field.value or "#14B8A6").strip()
            if not color.startswith("#"):
                color = f"#{color}"
            try:
                create_profile(name, color)
            except Exception as ex:
                ctx.app.show_snack(f"Erro ao criar perfil: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Perfil criado com sucesso!")
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    ft.Row([color_preview, color_field], spacing=12),
                    ft.Text("Cores sugeridas", size=12, color=theme_colors().text_muted),
                    color_swatches,
                    profile_modal_actions(ctx.app, "Criar", save),
                ],
                spacing=12,
                tight=True,
            ),
            title="Novo Perfil",
        )

    profile_list = ft.Column(spacing=8)
    for p in ctx.profiles:
        profile_list.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=p.color,
                            border_radius=6,
                        ),
                        ft.Text(p.name, expand=True, size=14, color=theme_colors().text_primary),
                        ft.IconButton(
                            ft.Icons.EDIT,
                            icon_size=18,
                            tooltip="Editar perfil",
                            on_click=lambda e, pid=p.id: edit_profile(ctx, pid),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            tooltip="Desativar perfil",
                            on_click=lambda e, pid=p.id: delete_profile(ctx, pid),
                        ),
                    ],
                    spacing=12,
                ),
                padding=12,
                bgcolor=theme_colors().surface_alt,
                border_radius=10,
                border=ft.Border.all(1, theme_colors().border),
            )
        )

    if not profile_list.controls:
        profile_list.controls.append(
            ft.Text("Nenhum perfil cadastrado. Adicione o primeiro.", color=theme_colors().text_muted, size=13)
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Perfis (Usuário 1, Usuário 2 + outros)", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            "Adicionar Perfil",
                            icon=ft.Icons.ADD,
                            on_click=add_profile,
                            style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                            icon_color=ft.Colors.WHITE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                profile_list,
            ],
            spacing=12,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=None,
    )

def edit_profile(ctx: SettingsCtx, profile_id: int):
    p = next((x for x in ctx.profiles if x.id == profile_id), None)
    if not p:
        return

    name_field = _modal_field(label="Nome", value=p.name)
    color_field = _modal_field(label="Cor (hex)", value=p.color)
    color_preview = ft.Container(width=24, height=24, bgcolor=p.color, border_radius=12)

    def on_color_change(ev):
        color = (color_field.value or p.color).strip()
        if not color.startswith("#"):
            color = f"#{color}"
        color_preview.bgcolor = color
        color_preview.update()

    color_field.on_change = on_color_change

    def save(ev):
        name = (name_field.value or "").strip()
        if not name:
            ctx.app.show_snack("Informe o nome do perfil", success=False)
            return
        color = (color_field.value or p.color).strip()
        if not color.startswith("#"):
            color = f"#{color}"
        if not update_profile(profile_id, name, color):
            ctx.app.show_snack("Não foi possível atualizar o perfil", success=False)
            return
        ctx.app.close_modal()
        ctx.app.show_snack("Perfil atualizado!")
        ctx.app.refresh_current_view()

    ctx.app.show_modal(
        ft.Column(
            [
                name_field,
                ft.Row([color_preview, color_field], spacing=12),
                profile_modal_actions(ctx.app, "Salvar", save),
            ],
            spacing=12,
            tight=True,
        ),
        title="Editar Perfil",
    )

def delete_profile(ctx: SettingsCtx, profile_id: int):
    p = next((x for x in ctx.profiles if x.id == profile_id), None)
    profile_name = p.name if p else "este perfil"

    def confirm(ev):
        if not deactivate_profile(profile_id):
            ctx.app.show_snack("Não foi possível desativar o perfil", success=False)
            return
        ctx.app.close_modal()
        ctx.app.show_snack("Perfil desativado (dados preservados)")
        ctx.app.refresh_current_view()

    ctx.app.show_modal(
        ft.Column(
            [
                _modal_text(f'Desativar o perfil "{profile_name}"? Os lançamentos serão mantidos.'),
                ft.Row(
                    [
                        ft.TextButton(
                            "Cancelar",
                            on_click=lambda _: ctx.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        _action_button("Desativar", confirm, bgcolor="#EF4444"),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title="Confirmar",
    )

def build_categories_section(ctx: SettingsCtx) -> ft.Container:
    def add_cat(e):
        def save(ev):
            name = (name_field.value or "").strip()
            if not name:
                ctx.app.show_snack("Informe o nome da categoria", success=False)
                return
            try:
                create_category(
                    name,
                    TransactionType(type_dropdown.value),
                    icon_field.value.strip() or None,
                )
            except Exception as ex:
                ctx.app.show_snack(f"Erro ao criar categoria: {ex}", success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack("Categoria criada!")
            ctx.app.refresh_current_view()

        name_field = _modal_field(label="Nome da Categoria")
        type_dropdown = _modal_dropdown(
            label="Tipo",
            options=[
                ft.dropdown.Option(TransactionType.INCOME.value, "Receita"),
                ft.dropdown.Option(TransactionType.EXPENSE.value, "Despesa"),
            ],
            value=TransactionType.EXPENSE.value,
        )
        icon_field = _modal_field(label="Ícone (emoji)", hint_text="🛒")

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    type_dropdown,
                    icon_field,
                    profile_modal_actions(ctx.app, "Criar Categoria", save),
                ],
                spacing=12,
                tight=True,
            ),
            title="Nova Categoria",
        )

    cat_list = ft.Column(spacing=6, height=220, scroll=ft.ScrollMode.AUTO)
    for c in ctx.categories:
        cat_list.controls.append(
            ft.Row(
                [
                    ft.Text(f"{c.icon or '📦'} {c.name}", expand=True, size=13, color=theme_colors().text_primary),
                    ft.Text("Receita" if c.type == TransactionType.INCOME else "Despesa", size=11, color=theme_colors().text_muted),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        on_click=lambda e, cid=c.id: delete_category(cid),
                    ),
                ],
                spacing=8,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Categorias", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            "Adicionar Categoria",
                            icon=ft.Icons.ADD,
                            on_click=add_cat,
                            style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                            icon_color=ft.Colors.WHITE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                cat_list,
            ],
            spacing=12,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=None,
    )

def delete_category(ctx: SettingsCtx, category_id: int):
    def confirm(ev):
        if delete_category(category_id):
            ctx.app.close_modal()
            ctx.app.show_snack("Categoria removida")
            ctx.app.refresh_current_view()
        else:
            ctx.app.close_modal()
            ctx.app.show_snack("Não é possível remover: categoria está em uso", success=False)

    ctx.app.show_modal(
        ft.Column(
            [
                _modal_text("Remover esta categoria? Lançamentos existentes não serão afetados."),
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
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title="Confirmar",
    )
