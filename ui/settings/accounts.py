"""Profile and bank account management."""

from __future__ import annotations

import flet as ft

from core.db.repositories.categories import create_category, delete_category
from core.db.repositories.profiles import create_profile, delete_profile as deactivate_profile, update_profile
from core.models import TransactionType

from core.i18n import t
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *


def build_profiles_section(ctx: SettingsCtx) -> ft.Container:
    def add_profile(e):
        name_field = _modal_field(label=t("settings.profile_name"), autofocus=True)
        color_field = _modal_field(label=t("settings.profile_color"), value=theme_colors().accent)
        color_preview = ft.Container(width=24, height=24, bgcolor=theme_colors().accent, border_radius=12)

        def on_color_change(ev):
            color = (color_field.value or theme_colors().accent).strip()
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
                    border=ft.Border.all(2, theme_colors().border),
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
                ctx.app.show_snack(t("settings.profile_need_name"), success=False)
                return
            color = (color_field.value or theme_colors().accent).strip()
            if not color.startswith("#"):
                color = f"#{color}"
            try:
                create_profile(name, color)
            except Exception as ex:
                ctx.app.show_snack(t("settings.profile_create_error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.profile_created"))
            ctx.app.refresh_current_view()

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    ft.Row([color_preview, color_field], spacing=12),
                    ft.Text(t("settings.profile_colors_hint"), size=12, color=theme_colors().text_muted),
                    color_swatches,
                    profile_modal_actions(ctx.app, t("common.create"), save),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.profile_new_title"),
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
                            tooltip=t("settings.profile_edit_tip"),
                            on_click=lambda e, pid=p.id: edit_profile(ctx, pid),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=18,
                            tooltip=t("settings.profile_deactivate_tip"),
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
            ft.Text(t("settings.profiles_empty"), color=theme_colors().text_muted, size=13)
        )

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(t("settings.profiles_title"), size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            t("settings.profiles_add"),
                            icon=ft.Icons.ADD,
                            on_click=add_profile,
                            style=primary_button_style(),
                            icon_color=theme_colors().on_accent,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                profile_list,
            ],
            spacing=12,
        ),
    )

def edit_profile(ctx: SettingsCtx, profile_id: int):
    p = next((x for x in ctx.profiles if x.id == profile_id), None)
    if not p:
        return

    name_field = _modal_field(label=t("common.name"), value=p.name)
    color_field = _modal_field(label=t("settings.profile_color"), value=p.color)
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
            ctx.app.show_snack(t("settings.profile_need_name"), success=False)
            return
        color = (color_field.value or p.color).strip()
        if not color.startswith("#"):
            color = f"#{color}"
        if not update_profile(profile_id, name, color):
            ctx.app.show_snack(t("settings.profile_update_fail"), success=False)
            return
        ctx.app.close_modal()
        ctx.app.show_snack(t("settings.profile_updated"))
        ctx.app.refresh_current_view()

    ctx.app.show_modal(
        ft.Column(
            [
                name_field,
                ft.Row([color_preview, color_field], spacing=12),
                profile_modal_actions(ctx.app, t("common.save"), save),
            ],
            spacing=12,
            tight=True,
        ),
        title=t("settings.profile_edit_title"),
    )

def delete_profile(ctx: SettingsCtx, profile_id: int):
    p = next((x for x in ctx.profiles if x.id == profile_id), None)
    profile_name = p.name if p else t("settings.profile_this")

    def confirm(ev):
        if not deactivate_profile(profile_id):
            ctx.app.show_snack(t("settings.profile_deactivate_fail"), success=False)
            return
        ctx.app.close_modal()
        ctx.app.show_snack(t("settings.profile_deactivated"))
        ctx.app.refresh_current_view()

    ctx.app.show_modal(
        ft.Column(
            [
                _modal_text(t("settings.profile_deactivate_q", name=profile_name)),
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"),
                            on_click=lambda _: ctx.app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        _danger_button(t("settings.profile_deactivate"), confirm),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title=t("common.confirm"),
    )

def build_categories_section(ctx: SettingsCtx) -> ft.Container:
    def add_cat(e):
        def save(ev):
            name = (name_field.value or "").strip()
            if not name:
                ctx.app.show_snack(t("settings.category_need_name"), success=False)
                return
            try:
                create_category(
                    name,
                    TransactionType(type_dropdown.value),
                    icon_field.value.strip() or None,
                )
            except Exception as ex:
                ctx.app.show_snack(t("settings.category_create_error", error=ex), success=False)
                return
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.category_created"))
            ctx.app.refresh_current_view()

        name_field = _modal_field(label=t("settings.category_name"))
        type_dropdown = _modal_dropdown(
            label=t("common.type"),
            options=[
                ft.dropdown.Option(TransactionType.INCOME.value, t("common.income")),
                ft.dropdown.Option(TransactionType.EXPENSE.value, t("common.expense")),
            ],
            value=TransactionType.EXPENSE.value,
        )
        icon_field = _modal_field(label=t("settings.category_icon"), hint_text="🛒")

        ctx.app.show_modal(
            ft.Column(
                [
                    name_field,
                    type_dropdown,
                    icon_field,
                    profile_modal_actions(ctx.app, t("settings.category_create"), save),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.category_new_title"),
        )

    cat_list = ft.Column(spacing=6, height=220, scroll=ft.ScrollMode.AUTO)
    for c in ctx.categories:
        cat_list.controls.append(
            ft.Row(
                [
                    ft.Text(
                        f"{c.icon or '📦'} {__import__('core.db.repositories.categories', fromlist=['display_name']).display_name(c)}",
                        expand=True,
                        size=13,
                        color=theme_colors().text_primary,
                    ),
                    ft.Text(t("common.income") if c.type == TransactionType.INCOME else t("common.expense"), size=11, color=theme_colors().text_muted),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        on_click=lambda e, cid=c.id: delete_category(cid),
                    ),
                ],
                spacing=8,
            )
        )

    return section_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(t("settings.categories_title"), size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                        ft.ElevatedButton(
                            t("settings.categories_add"),
                            icon=ft.Icons.ADD,
                            on_click=add_cat,
                            style=primary_button_style(),
                            icon_color=theme_colors().on_accent,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                cat_list,
            ],
            spacing=12,
        ),
    )

def delete_category(ctx: SettingsCtx, category_id: int):
    def confirm(ev):
        if delete_category(category_id):
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.category_removed"))
            ctx.app.refresh_current_view()
        else:
            ctx.app.close_modal()
            ctx.app.show_snack(t("settings.category_in_use"), success=False)

    ctx.app.show_modal(
        ft.Column(
            [
                _modal_text(t("settings.category_remove_q")),
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
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title=t("common.confirm"),
    )
