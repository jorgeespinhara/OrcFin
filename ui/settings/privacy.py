"""Privacy and local data transparency."""

from __future__ import annotations

import flet as ft

from core.audit_log import format_event_line, list_recent_events
from core.change_log import format_change_line, list_recent_changes
from core.db.repositories.ai_analyses import list_analyses
from core.data_export import export_open_data_json, export_transactions_csv
from core.paths import open_app_data_dir
from core.privacy import (
    describe_ai_status,
    describe_network_policy,
    describe_secret_storage,
    format_bytes,
    get_local_data_summary,
)
from ui.settings.context import SettingsCtx
from ui.settings.helpers import *

_AUDIT_HEIGHT = 140


def build_privacy_section(ctx: SettingsCtx) -> ft.Container:
    app = ctx.app
    summary = get_local_data_summary()
    audit_box = ft.Column(spacing=4, tight=True)
    change_box = ft.Column(spacing=4, tight=True)
    ai_box = ft.Column(spacing=4, tight=True)

    def refresh_audit():
        events = list_recent_events(15)
        if not events:
            audit_box.controls = [
                ft.Text("Nenhum evento externo registrado.", size=12, color=theme_colors().text_muted)
            ]
            return
        audit_box.controls = [
            ft.Text(format_event_line(row), size=11, color=theme_colors().text_secondary)
            for row in events
        ]

    def refresh_changes():
        rows = list_recent_changes(12)
        if not rows:
            change_box.controls = [
                ft.Text("Nenhuma alteração registrada.", size=12, color=theme_colors().text_muted)
            ]
            return
        change_box.controls = [
            ft.Text(format_change_line(row), size=11, color=theme_colors().text_secondary)
            for row in rows
        ]

    def refresh_ai_history():
        rows = list_analyses(limit=8)
        if not rows:
            ai_box.controls = [
                ft.Text("Nenhuma análise de IA salva.", size=12, color=theme_colors().text_muted)
            ]
            return
        ai_box.controls = [
            ft.Text(
                f"{row.get('created_at', '')}: {(row.get('summary') or '')[:120]}",
                size=11,
                color=theme_colors().text_secondary,
            )
            for row in rows
        ]

    def set_strict_offline(value: bool):
        app.settings["strict_offline"] = value
        app._save_settings()
        app.show_snack(
            "Modo offline estrito ativado." if value else "Chamadas externas permitidas novamente."
        )
        refresh_audit()

    def open_data_folder(_):
        try:
            open_app_data_dir()
        except Exception as ex:
            app.show_snack(f"Não foi possível abrir a pasta: {ex}", success=False)

    def export_all(_):
        try:
            pid = app.get_view_profile_id()
            csv_path = export_transactions_csv(pid)
            json_path = export_open_data_json(pid)
            app.show_snack(f"Exportado: {csv_path.name} e {json_path.name}")
        except Exception as ex:
            app.show_snack(f"Erro na exportação: {ex}", success=False)

    refresh_audit()
    refresh_changes()
    refresh_ai_history()

    db_size = format_bytes(int(summary["database_bytes"]))
    db_mtime = summary["database_modified"] or "n/d"

    return section_card(
        ft.Column(
            [
                ft.Text(
                    "Privacidade e dados",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme_colors().text_primary,
                ),
                ft.Text(
                    "Tudo abaixo é verificável no seu computador. O OrcFin não envia "
                    "lançamentos nem extratos para a nuvem.",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                ft.Text(f"Pasta de dados: {summary['data_root']}", size=12, color=theme_colors().text_secondary),
                ft.Text(f"Banco: {summary['database_path']}", size=12, color=theme_colors().text_muted),
                ft.Text(f"Tamanho: {db_size} · Última alteração: {db_mtime}", size=12, color=theme_colors().text_muted),
                ft.Text(f"Política de rede: {describe_network_policy(app.settings)}", size=12),
                ft.Text(f"Credenciais: {describe_secret_storage()}", size=12),
                ft.Text(f"IA: {describe_ai_status(app.settings)}", size=12),
                ft.Switch(
                    label="Nunca usar internet (modo offline estrito)",
                    value=bool(app.settings.get("strict_offline")),
                    active_color=_ACCENT,
                    label_text_style=switch_label_style(),
                    on_change=lambda e: set_strict_offline(bool(e.control.value)),
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Abrir pasta dos dados",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=open_data_folder,
                            style=on_surface_button_style(),
                        ),
                        ft.OutlinedButton(
                            "Exportar tudo (CSV + JSON)",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=export_all,
                            style=on_surface_button_style(),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                ),
                ft.Text(
                    "Para apagar todos os dados locais, use a Zona de perigo abaixo.",
                    size=11,
                    color=theme_colors().text_muted,
                ),
                ft.Text("Registro de eventos externos", size=13, weight=ft.FontWeight.W_600),
                ft.Container(
                    height=_AUDIT_HEIGHT,
                    content=ft.Column([audit_box], scroll=ft.ScrollMode.AUTO, spacing=4),
                    padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                    border=ft.Border.all(1, theme_colors().border),
                    border_radius=8,
                    bgcolor=theme_colors().surface_alt,
                ),
                ft.Text("Histórico de alterações locais", size=13, weight=ft.FontWeight.W_600),
                ft.Container(
                    height=_AUDIT_HEIGHT,
                    content=ft.Column([change_box], scroll=ft.ScrollMode.AUTO, spacing=4),
                    padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                    border=ft.Border.all(1, theme_colors().border),
                    border_radius=8,
                    bgcolor=theme_colors().surface_alt,
                ),
                ft.Text("Análises de IA (resumo local)", size=13, weight=ft.FontWeight.W_600),
                ft.Container(
                    height=100,
                    content=ft.Column([ai_box], scroll=ft.ScrollMode.AUTO, spacing=4),
                    padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                    border=ft.Border.all(1, theme_colors().border),
                    border_radius=8,
                    bgcolor=theme_colors().surface_alt,
                ),
            ],
            spacing=8,
        ),
    )


def build_privacy_backup_row(ctx: SettingsCtx) -> ft.Row:
    from ui.settings import system

    left = build_privacy_section(ctx)
    right = system.build_backup_section(ctx)
    left.expand = True
    right.expand = True
    return ft.Row(
        [left, right],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )