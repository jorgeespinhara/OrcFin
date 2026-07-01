"""First-run onboarding wizard."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from core.branding import APP_SUBTITLE, APP_VERSION
from core.paths import (
    get_app_data_dir,
    get_database_path,
    get_default_backup_dir,
    get_default_data_root,
    open_app_data_dir,
    set_data_root,
)
from core.db.repositories.profiles import get_all_profiles
from core.settings_store import load_settings, save_settings
from ui.mei.constants import PERSONAL_ACCENT
from ui.theme import active as theme_colors, title_text, body_text

_ONBOARDING_WIDTH = 480


def build_onboarding(app: "OrcFinApp") -> ft.Control:
    step = {"index": 0}
    setup_mode = {"value": app.settings.get("setup_mode") or "personal"}
    backup_on_close = {"value": bool(app.settings.get("backup_on_close"))}
    data_root = {"value": get_app_data_dir()}
    body = ft.Container(width=_ONBOARDING_WIDTH)
    path_field = ft.TextField(read_only=True, expand=True)
    db_label = ft.Text("", size=12)

    def sync_path_labels():
        path_field.value = str(data_root["value"])
        c = theme_colors()
        db_label.value = f"Banco: {get_database_path()}"
        db_label.color = c.text_muted

    def refresh_body():
        c = theme_colors()
        idx = step["index"]

        if idx == 0:
            body.content = ft.Column(
                [
                    title_text("Bem-vindo ao OrcFin", size=24),
                    body_text(f"Versão {APP_VERSION} · {APP_SUBTITLE}", size=13),
                    body_text(
                        "Seus dados ficam no computador. Nada é enviado à nuvem "
                        "para cadastro, importação ou relatórios.",
                        size=14,
                    ),
                ],
                spacing=12,
                tight=True,
            )
        elif idx == 1:
            options = ft.RadioGroup(
                value=setup_mode["value"],
                content=ft.Column(
                    [
                        ft.Radio(value="personal", label="Finanças pessoais"),
                        ft.Radio(value="mei", label="MEI (CNPJ)"),
                        ft.Radio(value="both", label="Pessoal + MEI"),
                        ft.Radio(value="couple", label="Casal / múltiplos perfis"),
                    ],
                    spacing=6,
                    tight=True,
                ),
                on_change=lambda e: setup_mode.update(value=e.control.value or "personal"),
            )
            body.content = ft.Column(
                [
                    title_text("Como você vai usar?", size=22),
                    body_text("Você pode mudar depois nas configurações.", size=13),
                    options,
                ],
                spacing=12,
                tight=True,
            )
        elif idx == 2:
            sync_path_labels()
            body.content = ft.Column(
                [
                    title_text("Onde ficam seus dados", size=22),
                    body_text(
                        f"Padrão no Windows: {get_default_data_root()}. "
                        "Escolha outra pasta se preferir.",
                        size=13,
                    ),
                    ft.Row([path_field], spacing=8),
                    db_label,
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Escolher pasta",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=_pick_data_folder,
                            ),
                            ft.TextButton(
                                "Abrir pasta",
                                on_click=lambda _: _open_folder(app),
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=12,
                tight=True,
            )
        elif idx == 3:
            backup_switch = ft.Switch(
                label="Backup ao fechar o app",
                value=backup_on_close["value"],
                active_color=PERSONAL_ACCENT,
                on_change=lambda e: backup_on_close.update(value=bool(e.control.value)),
            )
            body.content = ft.Column(
                [
                    title_text("Proteção dos dados", size=22),
                    body_text(
                        f"Backups ficam em {get_default_backup_dir()}. "
                        "Você pode alterar o local em Configurações.",
                        size=13,
                    ),
                    backup_switch,
                ],
                spacing=12,
                tight=True,
            )
        else:
            body.content = ft.Column(
                [
                    title_text("Primeiro passo", size=22),
                    body_text("Escolha como começar. Tudo pode ser feito depois no menu.", size=13),
                    ft.ElevatedButton(
                        "Importar extrato agora",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda _: _finish(app, setup_mode["value"], backup_on_close["value"], demo=False, import_now=True),
                        style=ft.ButtonStyle(bgcolor=PERSONAL_ACCENT, color=ft.Colors.WHITE),
                    ),
                    ft.OutlinedButton(
                        "Explorar com dados fictícios",
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                        on_click=lambda _: _finish(app, setup_mode["value"], backup_on_close["value"], demo=True, import_now=False),
                    ),
                    ft.TextButton(
                        "Pular e abrir o app",
                        on_click=lambda _: _finish(app, setup_mode["value"], backup_on_close["value"], demo=False, import_now=False),
                    ),
                ],
                spacing=10,
                tight=True,
            )

        nav_row.controls = _nav_buttons(idx)

    async def _pick_data_folder(_):
        picked = await ft.FilePicker().get_directory_path(
            dialog_title="Pasta dos dados do OrcFin",
            initial_directory=str(data_root["value"]),
        )
        if not picked:
            return
        try:
            set_data_root(Path(picked))
            from core.db.schema import init_database

            init_database()
            app.settings = load_settings()
            data_root["value"] = get_app_data_dir()
            sync_path_labels()
            app.profiles = get_all_profiles()
            refresh_body()
            app.page.update()
        except Exception as ex:
            app.show_snack(f"Não foi possível usar essa pasta: {ex}", success=False)

    def _nav_buttons(idx: int) -> list[ft.Control]:
        buttons: list[ft.Control] = []
        if idx > 0:
            buttons.append(ft.TextButton("Voltar", on_click=lambda _: _go(-1)))
        buttons.append(ft.Container(expand=True))
        if idx < 4:
            buttons.append(
                ft.ElevatedButton(
                    "Continuar",
                    on_click=lambda _: _go(1),
                    style=ft.ButtonStyle(bgcolor=PERSONAL_ACCENT, color=ft.Colors.WHITE),
                )
            )
        return buttons

    def _go(delta: int):
        step["index"] = max(0, min(4, step["index"] + delta))
        refresh_body()
        app.page.update()

    nav_row = ft.Row(spacing=8, width=_ONBOARDING_WIDTH)
    refresh_body()

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=body,
                    padding=ft.Padding(left=32, top=28, right=32, bottom=12),
                ),
                ft.Container(
                    content=nav_row,
                    padding=ft.Padding(left=32, right=32, bottom=24),
                ),
            ],
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )


def _open_folder(app: "OrcFinApp"):
    try:
        open_app_data_dir()
    except Exception as ex:
        app.show_snack(f"Não foi possível abrir a pasta: {ex}", success=False)


def _finish(app: "OrcFinApp", mode: str, backup: bool, *, demo: bool, import_now: bool):
    app.settings["setup_mode"] = mode
    app.settings["backup_on_close"] = backup
    app.settings["backup_dir"] = str(get_default_backup_dir())
    if mode == "mei":
        app.settings["app_mode"] = "mei"
    elif mode == "both":
        app.settings["app_mode"] = "personal"
    else:
        app.settings["app_mode"] = "personal"
    app.settings["onboarding_completed"] = True
    save_settings(app.settings)
    app.complete_onboarding(use_demo=demo, open_import=import_now)