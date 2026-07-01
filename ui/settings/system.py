"""Backup, import, AI providers, and app maintenance."""

from __future__ import annotations

import flet as ft

from datetime import datetime
from pathlib import Path
from core.ai_gateway import PROVIDERS, test_connection as test_provider_connection
from core.backup import (
    create_backup, find_latest_backup, inspect_backup, list_backups,
    prune_backups, restore_backup,
)
from core.data_export import export_open_data_json, export_transactions_csv
from core.reset import reset_clean_install, reset_database

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

def _backup_folder_path(ctx: SettingsCtx) -> Path | None:
    raw = ctx.app.settings.get("backup_dir")
    return Path(raw) if raw else None

def build_backup_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    backup_dir = app.settings.get("backup_dir") or "backups/ (padrão)"
    folder = _backup_folder_path(ctx)
    latest = find_latest_backup(folder)
    latest_label = latest.name if latest else "Nenhum backup encontrado"
    interval = int(app.settings.get("backup_interval_days") or 0)
    retention = int(app.settings.get("backup_retention_count") or 7)

    def run_backup(e):
        try:
            path = create_backup(folder)
            prune_backups(folder, retention)
            from datetime import datetime

            app.settings["last_backup_at"] = datetime.now().isoformat(timespec="seconds")
            app._save_settings()
            app.show_snack(f"Backup criado: {path.name}")
        except Exception as ex:
            app.show_snack(f"Erro no backup: {ex}", success=False)

    def open_restore_picker(e):
        backups = list_backups(folder)
        if not backups:
            app.show_snack("Nenhum backup para restaurar", success=False)
            return

        selected = {"path": backups[0]}
        preview = ft.Text("", size=12, color=theme_colors().text_secondary)

        def refresh_preview():
            try:
                info = inspect_backup(selected["path"])
                when = info.get("created_at") or "data desconhecida"
                preview.value = (
                    f"{info['transaction_count']} lançamentos • "
                    f"{info['profile_count']} perfis • {when}"
                )
            except Exception as ex:
                preview.value = f"Não foi possível ler o backup: {ex}"
            preview.update()

        def pick_backup(ev):
            selected["path"] = backups[int(ev.control.value)]
            refresh_preview()

        refresh_preview()

        def confirm_restore(ev):
            try:
                restore_backup(selected["path"])
                app.close_modal()
                app.show_snack("Backup restaurado! Reinicie o app.")
            except Exception as ex:
                app.show_snack(f"Erro: {ex}", success=False)

        app.show_modal(
            ft.Column(
                [
                    _modal_text("Selecione o backup. Os dados atuais serão substituídos."),
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
                            ft.TextButton("Cancelar", on_click=lambda _: app.close_modal(), style=on_surface_button_style()),
                            _action_button("Restaurar", confirm_restore, bgcolor="#EF4444"),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title="Restaurar backup",
        )

    backup_on_close = ft.Switch(
        label="Backup ao fechar o app",
        value=bool(app.settings.get("backup_on_close")),
        active_color=_ACCENT,
        label_text_style=switch_label_style(),
        on_change=lambda e: set_backup_on_close(ctx, e.control.value),
    )

    interval_dd = _modal_dropdown(
        label="Backup automático",
        value=str(interval),
        width=240,
        options=[
            ft.dropdown.Option("0", "Desligado"),
            ft.dropdown.Option("1", "Diário"),
            ft.dropdown.Option("7", "Semanal"),
        ],
        on_select=lambda e: set_backup_interval(ctx, int(e.control.value or 0)),
    )

    retention_f = _modal_field(
        label="Manter últimos N backups",
        value=str(retention),
        width=280,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_blur=lambda e: set_backup_retention(ctx, e.control.value or "7"),
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Backup Criptografado", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                ft.Text(f"Pasta: {backup_dir}", size=11, color=theme_colors().text_muted),
                ft.Text(f"Último arquivo: {latest_label}", size=11, color=theme_colors().text_muted),
                ft.Row(
                    [interval_dd, retention_f],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                backup_on_close,
                ft.Row(
                    [
                        ft.ElevatedButton("Criar backup agora", on_click=run_backup, style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE)),
                        ft.OutlinedButton("Restaurar backup…", on_click=open_restore_picker, style=on_surface_button_style()),
                    ],
                    spacing=12,
                ),
            ],
            spacing=10,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
    )

def build_export_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app

    def run_csv(_):
        try:
            path = export_transactions_csv(app.get_view_profile_id())
            app.show_snack(f"CSV exportado: {path}")
        except Exception as ex:
            app.show_snack(f"Erro na exportação: {ex}", success=False)

    def run_json(_):
        try:
            path = export_open_data_json(app.get_view_profile_id())
            app.show_snack(f"JSON exportado: {path}")
        except Exception as ex:
            app.show_snack(f"Erro na exportação: {ex}", success=False)

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Exportação aberta", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                ft.Text(
                    "Portabilidade dos seus dados (LGPD). Arquivos salvos em exports/.",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Exportar lançamentos (CSV)",
                            icon=ft.Icons.TABLE_ROWS,
                            on_click=run_csv,
                            style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                        ),
                        ft.OutlinedButton(
                            "Exportar dados (JSON)",
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
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
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
    button_color: str = "#EF4444",
    ) -> ft.Column:
    remove_lines = [ft.Text(f"• {item}", size=13, color=theme_colors().text_secondary) for item in removes]
    keep_block = []
    if keeps:
        keep_block = [
            ft.Text("Mantém:", size=13, weight=ft.FontWeight.W_600, color=theme_colors().text_muted),
            *[ft.Text(f"• {item}", size=13, color=theme_colors().text_muted) for item in keeps],
        ]

    return ft.Column(
        [
            ft.Text(title, size=17, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
            ft.Text(description, size=13, color=theme_colors().text_muted),
            ft.Text("Remove:", size=13, weight=ft.FontWeight.W_600, color=theme_colors().text_secondary),
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
                style=ft.ButtonStyle(bgcolor=button_color, color=ft.Colors.WHITE),
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
        label="Confirmação",
        hint_text=f"Digite {confirm_word} para confirmar",
        autofocus=True,
    )

    def run_action(ev):
        if (confirm_field.value or "").strip().upper() != confirm_word:
            app.show_snack(f"Digite {confirm_word} para confirmar", success=False)
            return
        try:
            on_confirm()
            app.close_modal()
        except Exception as ex:
            app.show_snack(f"Erro: {ex}", success=False)

    app.show_modal(
        ft.Column(
            [
                _modal_text(intro, size=13),
                _modal_text(
                    "Recomendamos criar um backup antes de continuar.",
                    size=12,
                    color=ft.Colors.AMBER_200,
                ),
                confirm_field,
                ft.Row(
                    [
                        ft.TextButton(
                            "Cancelar",
                            on_click=lambda _: app.close_modal(),
                            style=on_surface_button_style(),
                        ),
                        _action_button(action_label, run_action, bgcolor="#EF4444"),
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
        "Lançamentos, cartões e histórico de importação",
        "Orçamentos, metas e patrimônio (ativos/passivos)",
        "Perfil MEI, clientes, notas e obrigações",
        "Regras de categorização e perfis/categorias personalizados",
    ]
    financial_keeps = [
        "Chave e provedor de IA",
        "Pasta e backup automático ao fechar",
        "Tema e moeda",
        "Arquivos de backup já criados na pasta backups/",
    ]

    clean_removes = [
        "Tudo da opção anterior",
        "Arquivo de configurações (settings.json)",
        "Chave de API, provedor e modelo de IA",
        "Preferências de backup, filtros e modo do app",
    ]
    clean_keeps = [
        "Arquivos de backup já criados na pasta backups/ (não são apagados automaticamente)",
    ]

    def confirm_financial_reset(_):
        def do_reset():
            reset_database()
            app.apply_financial_reset()
            app.show_snack("Dados financeiros apagados.")

        open_reset_confirm(
            app,
            title="Zerar dados financeiros",
            intro=(
                "Os dados financeiros serão apagados e o banco recriado com perfis "
                "Usuário 1, Usuário 2 e categorias padrão. Suas configurações de IA e backup "
                "permanecem."
            ),
            confirm_word="ZERAR",
            action_label="Zerar dados",
            on_confirm=do_reset,
        )

    def confirm_clean_install(_):
        def do_reset():
            reset_clean_install()
            app.apply_clean_install_reset()
            app.show_snack("Instalação limpa concluída.")

        open_reset_confirm(
            app,
            title="Instalação limpa",
            intro=(
                "O app voltará ao estado de primeira instalação: banco zerado e "
                "configurações removidas. Nada do seu uso anterior permanecerá no app."
            ),
            confirm_word="LIMPAR",
            action_label="Instalação limpa",
            on_confirm=do_reset,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Zona de perigo", size=18, weight=ft.FontWeight.W_600, color="#EF4444"),
                ft.Text(
                    "Duas opções de reset. Escolha conforme o que deseja manter.",
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
                            border=ft.Border.all(1, "#334155"),
                            content=reset_option_card(
                                title="1. Zerar dados financeiros",
                                description="Apaga o banco e recomeça com perfis e categorias padrão.",
                                removes=financial_removes,
                                keeps=financial_keeps,
                                button_label="Zerar dados",
                                icon=ft.Icons.RESTORE,
                                on_click=confirm_financial_reset,
                                button_color="#DC2626",
                            ),
                        ),
                        ft.Container(
                            expand=1,
                            padding=16,
                            bgcolor=theme_colors().surface_alt,
                            border_radius=12,
                            border=ft.Border.all(1, "#334155"),
                            content=reset_option_card(
                                title="2. Instalação limpa",
                                description="Apaga banco e configurações, como na primeira abertura.",
                                removes=clean_removes,
                                keeps=clean_keeps,
                                button_label="Instalação limpa",
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=confirm_clean_install,
                                button_color="#991B1B",
                            ),
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=12,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=ft.Border.all(1, "#7F1D1D"),
    )

def build_ai_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    settings = app.settings
    provider_keys = dict(settings.get("ai_provider_keys") or {})
    provider_models = dict(settings.get("ai_provider_models") or {})
    provider_fields: dict[str, dict[str, ft.Control]] = {}

    def save_ai_config(_):
        keys: dict[str, str] = {}
        models: dict[str, str] = {}
        default_provider = None
        for provider_id, fields in provider_fields.items():
            key_val = (fields["key"].value or "").strip()
            model_val = (fields["model"].value or "").strip()
            if key_val:
                keys[provider_id] = key_val
                if default_provider is None:
                    default_provider = provider_id
            if model_val:
                models[provider_id] = model_val
        app.settings["ai_provider_keys"] = keys
        app.settings["ai_provider_models"] = models
        app.settings["ai_provider"] = default_provider
        app.settings["ai_api_key"] = keys.get(default_provider or "", "") or None
        app.settings["ai_model"] = models.get(default_provider or "", "") or None
        if default_provider:
            app.settings["ai_base_url"] = PROVIDERS.get(default_provider, {}).get("base_url")
        app._save_settings()
        app.show_snack("Chaves de IA salvas e criptografadas localmente.")

    provider_cards = []
    for provider_id, meta in PROVIDERS.items():
        key_field = _modal_field(
            label="API Key",
            value=provider_keys.get(provider_id, ""),
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        model_field = _modal_field(
            label="Modelo (opcional)",
            value=provider_models.get(provider_id, ""),
            hint_text=meta.get("default_model", ""),
            width=220,
        )

        def make_test(pid: str, key_control: ft.TextField, provider_name: str):
            def test_connection(_):
                if not (key_control.value or "").strip():
                    app.show_snack("Insira a API key deste provedor.", success=False)
                    return
                result = test_provider_connection(pid, key_control.value.strip())
                if result["success"]:
                    app.show_snack(f"{provider_name}: {result['message']}")
                else:
                    app.show_snack(
                        f"{provider_name}: {result.get('error', 'Erro desconhecido')}",
                        success=False,
                    )
            return test_connection

        provider_fields[provider_id] = {"key": key_field, "model": model_field}
        status = (
            ft.Text("Configurado", size=11, color="#22C55E")
            if provider_keys.get(provider_id)
            else ft.Text("Sem chave", size=11, color=theme_colors().text_muted)
        )
        provider_cards.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(meta["name"], size=14, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                                status,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(meta.get("pricing_hint", ""), size=11, color=theme_colors().text_muted),
                        ft.Row([key_field, model_field], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                        ft.Row(
                            [
                                ft.OutlinedButton(
                                    "Testar conexão",
                                    on_click=make_test(provider_id, key_field, meta["name"]),
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
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Integração com Inteligência Artificial", size=16, weight=ft.FontWeight.W_600, color=theme_colors().text_primary),
                ft.Text(
                    "Cada provedor usa sua própria API key (armazenada só no seu PC). "
                    "O OrcFin envia apenas totais agregados, nunca lançamentos individuais. "
                    "O chat gratuito do site não pode ser acionado pelo app; use a API key do provedor.",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                *provider_cards,
                ft.ElevatedButton(
                    "Salvar chaves de IA",
                    on_click=save_ai_config,
                    style=ft.ButtonStyle(bgcolor=_ACCENT, color=ft.Colors.WHITE),
                ),
            ],
            spacing=12,
        ),
        padding=24,
        bgcolor=theme_colors().surface,
        border_radius=16,
        border=None,
    )
