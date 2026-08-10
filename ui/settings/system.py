"""Backup, import, AI providers, and app maintenance."""

from __future__ import annotations

import flet as ft

from datetime import datetime
from pathlib import Path
from core.ai.providers import pricing_hint
from core.ai_gateway import PROVIDERS, test_connection as test_provider_connection
from core.backup import (
    create_backup, find_latest_backup, inspect_backup, list_backups,
    preview_backup, prune_backups, restore_backup,
)
from core.backup_health import assess_backup_health
from core.data_export import export_open_data_json, export_transactions_csv
from core.privacy import describe_secret_storage
from core.reset import reset_clean_install, reset_database

from core.i18n import t
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *


def set_backup_on_close(ctx: SettingsCtx, value: bool):
    ctx.app.settings["backup_on_close"] = value
    ctx.app._save_settings()

def set_backup_interval(ctx: SettingsCtx, days: int) -> None:
    ctx.app.settings["backup_interval_days"] = days
    ctx.app._save_settings()

def set_backup_retention(ctx: SettingsCtx, value: str) -> None:
    try:
        keep = max(3, min(30, int(value)))
    except ValueError:
        keep = 7
    ctx.app.settings["backup_retention_count"] = keep
    ctx.app._save_settings()

async def _pick_backup_dir(ctx: SettingsCtx):
    app = ctx.app
    folder = _backup_folder_path(ctx)
    picked = await ft.FilePicker().get_directory_path(
        dialog_title=t("settings.backup_folder_dialog"),
        initial_directory=str(folder) if folder else None,
    )
    if not picked:
        return
    app.settings["backup_dir"] = picked
    app._save_settings()
    app.show_snack(t("settings.backup_folder_updated"))
    app.refresh_current_view()


def _backup_folder_path(ctx: SettingsCtx) -> Path | None:
    raw = ctx.app.settings.get("backup_dir")
    return Path(raw) if raw else None

def build_backup_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    backup_dir = app.settings.get("backup_dir") or t("settings.backup_dir_default")
    folder = _backup_folder_path(ctx)
    latest = find_latest_backup(folder)
    latest_label = latest.name if latest else t("settings.backup_none")
    interval = int(app.settings.get("backup_interval_days") or 0)
    retention = int(app.settings.get("backup_retention_count") or 7)
    health = assess_backup_health(app.settings)
    c = theme_colors()
    level_colors = {
        "otimo": c.success,
        "bom": c.accent,
        "atencao": c.warning,
        "critico": c.danger,
    }
    health_color = level_colors.get(health["level"], theme_colors().text_muted)
    recs = health.get("recommendations") or []
    health_detail = recs[0] if recs else t("settings.backup_protected")
    if health.get("age_days") is not None and not recs:
        health_detail = t("settings.backup_age", days=health["age_days"])
    next_days = health.get("days_until_next")
    if next_days is not None and health.get("auto_enabled"):
        health_detail += t("settings.backup_next", days=next_days)

    def run_backup(e):
        try:
            path = create_backup(folder)
            prune_backups(folder, retention)
            from datetime import datetime

            app.settings["last_backup_at"] = datetime.now().isoformat(timespec="seconds")
            app._save_settings()
            app.show_snack(t("settings.backup_created", name=path.name))
        except Exception as ex:
            app.show_snack(t("settings.backup_error", error=ex), success=False)

    def open_restore_picker(e):
        backups = list_backups(folder)
        if not backups:
            app.show_snack(t("settings.backup_none_restore"), success=False)
            return

        selected = {"path": backups[0]}
        preview = ft.Text("", size=12, color=theme_colors().text_secondary)

        def refresh_preview():
            try:
                info = inspect_backup(selected["path"])
                when = info.get("created_at") or t("common.unknown_date")
                preview.value = t(
                    "settings.backup_preview",
                    tx=info["transaction_count"],
                    profiles=info["profile_count"],
                    when=when,
                )
            except Exception as ex:
                preview.value = t("settings.backup_read_fail", error=ex)
            preview.update()

        def pick_backup(ev):
            selected["path"] = backups[int(ev.control.value)]
            refresh_preview()

        refresh_preview()

        def run_restore():
            try:
                restore_backup(selected["path"])
                app.show_snack(t("settings.backup_restored"))
            except Exception as ex:
                app.show_snack(t("common.error", error=ex), success=False)

        def proceed_restore(_):
            app.close_modal()
            open_reset_confirm(
                app,
                title=t("settings.backup_restore_title"),
                intro=t("settings.backup_restore_intro"),
                confirm_word=t("settings.backup_restore_word"),
                action_label=t("settings.backup_restore_action"),
                on_confirm=run_restore,
            )

        app.show_modal(
            ft.Column(
                [
                    _modal_text(t("settings.backup_select")),
                    ft.Dropdown(
                        value="0",
                        options=[
                            ft.dropdown.Option(str(i), b.name)
                            for i, b in enumerate(backups[:15])
                        ],
                        on_select=pick_backup,
                        width=420,
                    ),
                    preview,
                    ft.Row(
                        [
                            ft.TextButton(t("common.cancel"), on_click=lambda _: app.close_modal(), style=on_surface_button_style()),
                            _danger_button(t("settings.backup_continue"), proceed_restore),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.backup_restore_modal"),
        )

    def open_backup_test(e):
        backups = list_backups(folder)
        if not backups:
            app.show_snack(t("settings.backup_none_test"), success=False)
            return
        selected = {"path": backups[0]}
        preview = ft.Text("", size=12, color=theme_colors().text_secondary)

        def refresh_preview():
            try:
                info = preview_backup(selected["path"])
                when = info.get("created_at") or t("common.unknown_date")
                size_kb = int(info.get("file_size") or 0) // 1024
                period = ""
                if info.get("date_min") and info.get("date_max"):
                    period = f" · {info['date_min']} → {info['date_max']}"
                names = ", ".join(info.get("profile_names") or [])[:80]
                preview.value = t(
                    "settings.backup_test_preview",
                    tx=info["transaction_count"],
                    profiles=info["profile_count"],
                    period=period,
                    when=when,
                    size_kb=size_kb,
                ) + (t("settings.backup_profiles_line", names=names) if names else "")
            except Exception as ex:
                preview.value = t("settings.backup_invalid", error=ex)
            if preview.page:
                preview.update()

        def pick_backup(ev):
            selected["path"] = backups[int(ev.control.value)]
            refresh_preview()

        refresh_preview()
        app.show_modal(
            ft.Column(
                [
                    _modal_text(t("settings.backup_test_intro"), size=12,),
                    ft.Dropdown(
                        value="0",
                        options=[ft.dropdown.Option(str(i), b.name) for i, b in enumerate(backups[:15])],
                        on_select=pick_backup,
                        width=420,
                    ),
                    preview,
                    ft.Row(
                        [
                            ft.TextButton(
                                t("common.close"),
                                on_click=lambda _: app.close_modal(),
                                style=on_surface_button_style(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("settings.backup_test_title"),
        )

    backup_on_close = ft.Switch(
        label=t("settings.backup_on_close"),
        value=bool(app.settings.get("backup_on_close")),
        active_color=_ACCENT,
        label_text_style=switch_label_style(),
        on_change=lambda e: set_backup_on_close(ctx, e.control.value),
    )

    interval_dd = _modal_dropdown(
        label=t("settings.backup_auto"),
        value=str(interval),
        width=240,
        options=[
            ft.dropdown.Option("0", t("settings.backup_off")),
            ft.dropdown.Option("1", t("settings.backup_daily")),
            ft.dropdown.Option("7", t("settings.backup_weekly")),
        ],
        on_select=lambda e: set_backup_interval(ctx, int(e.control.value or 0)),
    )

    retention_f = _modal_field(
        label=t("settings.backup_retention"),
        value=str(retention),
        width=280,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=lambda e: set_backup_retention(ctx, e.control.value or "7"),
    )

    return section_card(
        ft.Column(
            [
                ft.Text(t("settings.backup_title"), size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SHIELD, size=18, color=health_color),
                        ft.Text(
                            t("settings.backup_protection", label={"otimo": t("settings.backup_level_otimo"), "bom": t("settings.backup_level_bom"), "atencao": t("settings.backup_level_atencao"), "critico": t("settings.backup_level_critico")}.get(health["level"], health["label"])),
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=health_color,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Text(health_detail, size=11, color=theme_colors().text_secondary),
                ft.Text(t("settings.backup_folder", path=backup_dir), size=11, color=theme_colors().text_muted),
                ft.OutlinedButton(
                    t("settings.backup_choose_folder"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda e: app.page.run_task(_pick_backup_dir, ctx),
                    style=on_surface_button_style(),
                ),
                ft.Text(t("settings.backup_latest_file", name=latest_label), size=11, color=theme_colors().text_muted),
                ft.Text(
                    t("settings.backup_crypto_note"),
                    size=10,
                    color=theme_colors().text_muted,
                ),
                ft.Row(
                    [interval_dd, retention_f],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                backup_on_close,
                ft.Row(
                    [
                        ft.ElevatedButton(t("settings.backup_create_now"), on_click=run_backup, style=primary_button_style()),
                        ft.OutlinedButton(t("settings.backup_test_btn"), on_click=open_backup_test, style=on_surface_button_style()),
                        ft.OutlinedButton(t("settings.backup_restore_btn"), on_click=open_restore_picker, style=on_surface_button_style()),
                    ],
                    spacing=12,
                ),
            ],
            spacing=10,
        ),
    )

def build_export_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app

    def run_csv(_):
        try:
            path = export_transactions_csv(app.get_view_profile_id())
            app.show_snack(t("settings.export_csv_ok", path=path))
        except Exception as ex:
            app.show_snack(t("settings.export_error", error=ex), success=False)

    def run_json(_):
        try:
            path = export_open_data_json(app.get_view_profile_id())
            app.show_snack(t("settings.export_json_ok", path=path))
        except Exception as ex:
            app.show_snack(t("settings.export_error", error=ex), success=False)

    return section_card(
        ft.Column(
            [
                ft.Text(t("settings.export_title"), size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                ft.Text(
                    t("settings.export_body"),
                    size=11,
                    color=theme_colors().text_muted,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            t("settings.export_csv"),
                            icon=ft.Icons.TABLE_ROWS,
                            on_click=run_csv,
                            style=primary_button_style(),
                        ),
                        ft.OutlinedButton(
                            t("settings.export_json"),
                            icon=ft.Icons.DATA_OBJECT,
                            on_click=run_json,
                            style=on_surface_button_style(),
                        ),
                    ],
                    spacing=12,
                    wrap=True,
                ),
            ],
            spacing=10,
        ),
    )


def reset_option_card(
    *,
    title: str,
    description: str,
    removes: list[str],
    keeps: list[str] | None,
    button_label: str,
    icon,
    on_click,
    button_color: str | None = None,
    ) -> ft.Column:
    if button_color is None:
        button_color = theme_colors().danger
    remove_lines = [ft.Text(f"• {item}", size=13, color=theme_colors().text_secondary) for item in removes]
    keep_block = []
    if keeps:
        keep_block = [
            ft.Text(t("common.keeps"), size=13, weight=ft.FontWeight.W_600, color=theme_colors().text_muted),
            *[ft.Text(f"• {item}", size=13, color=theme_colors().text_muted) for item in keeps],
        ]

    return ft.Column(
        [
            ft.Text(title, size=17, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
            ft.Text(description, size=13, color=theme_colors().text_muted),
            ft.Text(t("common.removes"), size=13, weight=ft.FontWeight.W_600, color=theme_colors().text_secondary),
            ft.Container(
                height=RESET_BULLETS_HEIGHT,
                content=ft.Column(
                    [*remove_lines, *keep_block],
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            ft.ElevatedButton(
                button_label,
                icon=icon,
                on_click=on_click,
                style=primary_button_style(bgcolor=button_color),
            ),
        ],
        spacing=8,
        tight=True,
    )

def open_reset_confirm(app,
    *,
    title: str,
    intro: str,
    confirm_word: str,
    action_label: str,
    on_confirm,
    ):
    confirm_field = _modal_field(
        label=t("settings.reset_confirm_label"),
        hint_text=t("settings.reset_confirm_hint", word=confirm_word),
        autofocus=True,
    )

    def run_action(ev):
        if (confirm_field.value or "").strip().upper() != confirm_word:
            app.show_snack(t("settings.reset_confirm_snack", word=confirm_word), success=False)
            return
        try:
            on_confirm()
            app.close_modal()
        except Exception as ex:
            app.show_snack(t("common.error", error=ex), success=False)

    app.show_modal(
        ft.Column(
            [
                _modal_text(intro, size=13),
                _modal_text(t("settings.reset_backup_hint"), size=12, color=theme_colors().warning,),
                confirm_field,
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"),
                            on_click=lambda _: app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        _danger_button(action_label, run_action),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        title=title,
    )

def build_danger_zone_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    financial_removes = [
        t("settings.reset_fin_r1"),
        t("settings.reset_fin_r2"),
        t("settings.reset_fin_r3"),
        t("settings.reset_fin_r4"),
    ]
    financial_keeps = [
        t("settings.reset_fin_k1"),
        t("settings.reset_fin_k2"),
        t("settings.reset_fin_k3"),
        t("settings.reset_fin_k4"),
    ]

    clean_removes = [
        t("settings.reset_clean_r1"),
        t("settings.reset_clean_r2"),
        t("settings.reset_clean_r3"),
        t("settings.reset_clean_r4"),
    ]
    clean_keeps = [
        t("settings.reset_clean_k1"),
    ]

    def confirm_financial_reset(_):
        def do_reset():
            reset_database()
            app.apply_financial_reset()
            app.show_snack(t("settings.reset_fin_done"))

        open_reset_confirm(
            app,
            title=t("settings.reset_fin_modal_title"),
            intro=t("settings.reset_fin_intro"),
            confirm_word=t("settings.reset_fin_word"),
            action_label=t("settings.reset_fin_btn"),
            on_confirm=do_reset,
        )

    def confirm_clean_install(_):
        def do_reset():
            reset_clean_install()
            app.apply_clean_install_reset()
            app.show_snack(t("settings.reset_clean_done"))

        open_reset_confirm(
            app,
            title=t("settings.reset_clean_modal_title"),
            intro=t("settings.reset_clean_intro"),
            confirm_word=t("settings.reset_clean_word"),
            action_label=t("settings.reset_clean_btn"),
            on_confirm=do_reset,
        )

    return section_card(
        ft.Column(
            [
                ft.Text(t("settings.danger_zone_title"), size=18, weight=ft.FontWeight.W_600, color=theme_colors().danger),
                ft.Text(
                    t("settings.danger_zone_body"),
                    size=13,
                    color=theme_colors().text_muted,
                ),
                ft.Row(
                    [
                        ft.Container(
                            expand=1,
                            padding=16,
                            bgcolor=theme_colors().surface_alt,
                            border_radius=12,
                            border=ft.Border.all(1, theme_colors().border),
                            content=reset_option_card(
                                title=t("settings.reset_fin_title"),
                                description=t("settings.reset_fin_desc"),
                                removes=financial_removes,
                                keeps=financial_keeps,
                                button_label=t("settings.reset_fin_btn"),
                                icon=ft.Icons.RESTORE,
                                on_click=confirm_financial_reset,
                                button_color=theme_colors().danger,
                            ),
                        ),
                        ft.Container(
                            expand=1,
                            padding=16,
                            bgcolor=theme_colors().surface_alt,
                            border_radius=12,
                            border=ft.Border.all(1, theme_colors().border),
                            content=reset_option_card(
                                title=t("settings.reset_clean_title"),
                                description=t("settings.reset_clean_desc"),
                                removes=clean_removes,
                                keeps=clean_keeps,
                                button_label=t("settings.reset_clean_btn"),
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=confirm_clean_install,
                                button_color=theme_colors().error_banner_border,
                            ),
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=12,
        ),
        border=ft.Border.all(1, theme_colors().danger),
    )

def build_ai_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    settings = app.settings
    provider_keys = dict(settings.get("ai_provider_keys") or {})
    provider_models = dict(settings.get("ai_provider_models") or {})
    initial = settings.get("ai_provider") or next(
        (p for p in PROVIDERS if provider_keys.get(p)),
        next(iter(PROVIDERS)),
    )
    selected = {"id": initial}
    draft = {
        pid: {
            "key": provider_keys.get(pid, ""),
            "model": provider_models.get(pid, ""),
        }
        for pid in PROVIDERS
    }
    initial_meta = PROVIDERS[initial]
    configured_names = [PROVIDERS[p]["name"] for p in PROVIDERS if draft[p]["key"]]

    key_field = _modal_field(
        label=t("settings.ai_key"),
        value=draft[initial]["key"],
        password=True,
        can_reveal_password=True,
        expand=True,
    )
    model_field = _modal_field(
        label=t("settings.ai_model"),
        value=draft[initial]["model"],
        hint_text=initial_meta.get("default_model", ""),
        width=220,
    )
    hint_text = ft.Text(
        pricing_hint(initial_meta),
        size=11,
        color=theme_colors().text_muted,
    )
    status_text = ft.Text(
        t("settings.ai_key_ok") if draft[initial]["key"] else t("settings.ai_key_missing"),
        size=11,
        color=theme_colors().success if draft[initial]["key"] else theme_colors().text_muted,
    )
    configured_hint = ft.Text(
        t("settings.ai_configured", names=", ".join(configured_names)) if configured_names else t("settings.ai_none"),
        size=11,
        color=theme_colors().text_secondary,
    )

    def flush_draft() -> None:
        pid = selected["id"]
        draft[pid]["key"] = (key_field.value or "").strip()
        draft[pid]["model"] = (model_field.value or "").strip()

    def refresh_configured_hint() -> None:
        names = [PROVIDERS[p]["name"] for p in PROVIDERS if draft[p]["key"]]
        configured_hint.value = t("settings.ai_configured", names=", ".join(names)) if names else t("settings.ai_none")

    def load_provider(pid: str) -> None:
        meta = PROVIDERS[pid]
        key_field.value = draft[pid]["key"]
        model_field.value = draft[pid]["model"]
        model_field.hint_text = meta.get("default_model", "")
        hint_text.value = pricing_hint(meta)
        if draft[pid]["key"]:
            status_text.value = t("settings.ai_key_ok")
            status_text.color = theme_colors().success
        else:
            status_text.value = t("settings.ai_key_missing")
            status_text.color = theme_colors().text_muted

    def on_provider_pick(e):
        if not e.control.page:
            return
        flush_draft()
        selected["id"] = e.control.value
        load_provider(selected["id"])
        refresh_configured_hint()
        app.page.update()

    def save_ai_config(_):
        flush_draft()
        keys = {p: d["key"] for p, d in draft.items() if d["key"]}
        models = {p: d["model"] for p, d in draft.items() if d["model"]}
        default_provider = selected["id"] if keys.get(selected["id"]) else next(iter(keys), None)
        app.settings["ai_provider_keys"] = keys
        app.settings["ai_provider_models"] = models
        app.settings["ai_provider"] = default_provider
        app.settings["ai_api_key"] = keys.get(default_provider or "", "") or None
        app.settings["ai_model"] = models.get(default_provider or "", "") or None
        if default_provider:
            app.settings["ai_base_url"] = PROVIDERS.get(default_provider, {}).get("base_url")
        app._save_settings()
        refresh_configured_hint()
        app.page.update()
        app.show_snack(t("settings.ai_saved", detail=describe_secret_storage()))

    def test_connection(_):
        flush_draft()
        pid = selected["id"]
        meta = PROVIDERS[pid]
        key = draft[pid]["key"]
        if not key:
            app.show_snack(t("settings.ai_need_key"), success=False)
            return
        result = test_provider_connection(pid, key, settings=app.settings)
        if result["success"]:
            app.show_snack(f"{meta['name']}: {result['message']}")
        else:
            app.show_snack(
                f"{meta['name']}: {result.get('error', t('settings.ai_unknown_error'))}",
                success=False,
            )

    provider_dd = _modal_dropdown(
        label=t("settings.ai_provider"),
        value=initial,
        width=320,
        options=[ft.dropdown.Option(pid, meta["name"]) for pid, meta in PROVIDERS.items()],
        on_select=on_provider_pick,
    )

    config_panel = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        status_text,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
                hint_text,
                ft.Row(
                    [key_field, model_field],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            t("settings.ai_test"),
                            on_click=test_connection,
                            style=on_surface_button_style(),
                        ),
                    ],
                ),
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor=theme_colors().surface_alt,
        border_radius=12,
        border=ft.Border.all(1, theme_colors().border),
    )

    return section_card(
        ft.Column(
            [
                ft.Text(
                    t("settings.ai_title"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme_colors().text_primary,
                ),
                ft.Text(
                    t("settings.ai_body"),
                    size=11,
                    color=theme_colors().text_muted,
                ),
                provider_dd,
                configured_hint,
                config_panel,
                ft.ElevatedButton(
                    t("settings.ai_save"),
                    on_click=save_ai_config,
                    style=primary_button_style(),
                ),
            ],
            spacing=12,
        ),
    )
