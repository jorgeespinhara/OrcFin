"""First-run onboarding wizard."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from core.branding import APP_VERSION
from core.i18n import (
    COUNTRY_PRESETS,
    apply_from_settings,
    detect_system_country,
    supports_mei,
    t,
)
from core.mei_operational import profile_hint as mei_profile_hint
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
from ui.mei.operational_profile import cnae_field, profile_radio_group, suggest_from_cnae
from ui.theme import active as theme_colors, title_text, body_text, primary_button_style

_ONBOARDING_WIDTH = 440

# Badge colors (readable on dark/light; not real flag art — Windows often fails emoji flags)
_COUNTRY_BADGE = {
    "BR": ("#009C3B", "#FFFFFF"),
    "US": ("#1D4ED8", "#FFFFFF"),
    "ES": ("#C2410C", "#FFFFFF"),
}


def _step_flow(mode: str, country: str) -> list[str]:
    # Welcome includes country/locale selection — first interactive choice.
    steps = ["welcome", "mode"]
    if supports_mei(country) and mode in ("mei", "both"):
        steps.append("mei_profile")
    steps.extend(["data", "backup", "start"])
    return steps


def _country_option_card(
    code: str,
    *,
    selected: bool,
    on_pick,
    colors,
) -> ft.Control:
    """Full-width selectable country row — no emoji flags (broken as BR/US/ES on Windows)."""
    preset = COUNTRY_PRESETS[code]
    badge_bg, badge_fg = _COUNTRY_BADGE.get(code, (PERSONAL_ACCENT, "#FFFFFF"))
    # Native name always (not t()) so picker is clear before language is chosen.
    name = str(preset.get("native_name") or t(preset["name_key"]))
    meta = f"{preset['locale']}  ·  {preset['currency']}"
    border = PERSONAL_ACCENT if selected else colors.border
    bg = colors.surface if selected else colors.surface_alt

    badge = ft.Container(
        content=ft.Text(
            code,
            size=12,
            weight=ft.FontWeight.W_700,
            color=badge_fg,
            text_align=ft.TextAlign.CENTER,
        ),
        width=40,
        height=40,
        border_radius=10,
        bgcolor=badge_bg,
        alignment=ft.Alignment.CENTER,
    )
    labels = ft.Column(
        [
            ft.Text(name, size=15, weight=ft.FontWeight.W_600, color=colors.text_primary),
            ft.Text(meta, size=12, color=colors.text_muted),
        ],
        spacing=2,
        tight=True,
        expand=True,
    )
    trailing = ft.Icon(
        ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
        color=PERSONAL_ACCENT if selected else colors.text_muted,
        size=22,
    )
    return ft.Container(
        content=ft.Row(
            [badge, labels, trailing],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(14, 12, 14, 12),
        border_radius=12,
        bgcolor=bg,
        border=ft.Border.all(2 if selected else 1, border),
        on_click=lambda _e, code=code: on_pick(code),
        ink=True,
        width=_ONBOARDING_WIDTH,
    )


def _country_picker(selected: str, on_pick, *, colors) -> ft.Control:
    cards = [
        _country_option_card(code, selected=(code == selected), on_pick=on_pick, colors=colors)
        for code in COUNTRY_PRESETS
    ]
    return ft.Column(
        [
            ft.Text(
                t("onboarding.language_title"),
                size=14,
                weight=ft.FontWeight.W_600,
                color=colors.text_primary,
            ),
            # Always trilingual so a first-time visitor never depends on the default language.
            ft.Text(
                t("onboarding.language_hint_multi"),
                size=12,
                color=colors.text_muted,
            ),
            ft.Column(cards, spacing=10, tight=True),
        ],
        spacing=10,
        tight=True,
    )


def _seed_onboarding_locale(app: "OrcFinApp") -> str:
    """First paint: follow OS language when the user has not chosen a country yet."""
    if app.settings.get("onboarding_locale_seeded"):
        return app.settings.get("country_profile") or "BR"
    code = detect_system_country()
    preset = COUNTRY_PRESETS[code]
    app.settings["country_profile"] = code
    app.settings["locale"] = preset["locale"]
    app.settings["currency"] = preset["currency"]
    app.settings["onboarding_locale_seeded"] = True
    apply_from_settings(app.settings)
    return code


def build_onboarding(app: "OrcFinApp") -> ft.Control:
    step = {"index": 0}
    setup_mode = {"value": app.settings.get("setup_mode") or "personal"}
    backup_on_close = {"value": bool(app.settings.get("backup_on_close"))}
    mei_operational = {"value": app.settings.get("mei_operational_profile") or "on_demand"}
    mei_cnae = {"value": app.settings.get("mei_cnae") or ""}
    country = {"value": _seed_onboarding_locale(app)}
    data_root = {"value": get_app_data_dir()}
    body = ft.Container(width=_ONBOARDING_WIDTH)
    path_field = ft.TextField(read_only=True, expand=True)
    db_label = ft.Text("", size=12)
    profile_hint = ft.Text("", size=12)

    def _country() -> str:
        return country["value"] or "BR"

    def _apply_country_choice(code: str) -> None:
        preset = COUNTRY_PRESETS[code]
        country["value"] = code
        app.settings["country_profile"] = code
        app.settings["locale"] = preset["locale"]
        app.settings["currency"] = preset["currency"]
        apply_from_settings(app.settings)
        if not supports_mei(code) and setup_mode["value"] in ("mei", "both"):
            setup_mode["value"] = "personal"
        refresh_body()
        app.page.update()

    def sync_path_labels():
        path_field.value = str(data_root["value"])
        c = theme_colors()
        db_label.value = t("onboarding.db_label", path=get_database_path())
        db_label.color = c.text_muted

    def sync_profile_hint():
        key = mei_operational["value"]
        profile_hint.value = mei_profile_hint(key)
        profile_hint.color = theme_colors().text_muted

    def refresh_body():
        c = theme_colors()
        flow = _step_flow(setup_mode["value"], _country())
        step_id = flow[step["index"]]

        if step_id == "welcome":
            body.content = ft.Column(
                [
                    title_text(t("onboarding.welcome_title"), size=24),
                    body_text(f"v{APP_VERSION} · {t('app.subtitle')}", size=13),
                    body_text(t("onboarding.welcome_body"), size=14),
                    ft.Container(height=8),
                    _country_picker(_country(), _apply_country_choice, colors=c),
                ],
                spacing=10,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            )
        elif step_id == "mode":
            radios = [
                ft.Radio(value="personal", label=t("onboarding.mode_personal")),
                ft.Radio(value="couple", label=t("onboarding.mode_couple")),
            ]
            if supports_mei(_country()):
                radios.insert(1, ft.Radio(value="mei", label=t("onboarding.mode_mei")))
                radios.insert(2, ft.Radio(value="both", label=t("onboarding.mode_both")))
            mode_value = setup_mode["value"]
            if mode_value not in {r.value for r in radios}:
                mode_value = "personal"
                setup_mode["value"] = mode_value
            options = ft.RadioGroup(
                value=mode_value,
                content=ft.Column(radios, spacing=6, tight=True),
                on_change=lambda e: setup_mode.update(value=e.control.value or "personal"),
            )
            body.content = ft.Column(
                [
                    title_text(t("onboarding.mode_title"), size=22),
                    body_text(t("onboarding.mode_body"), size=13),
                    options,
                ],
                spacing=12,
                tight=True,
            )
        elif step_id == "mei_profile":
            sync_profile_hint()
            cnae_input = cnae_field(
                value=mei_cnae["value"],
                on_change=lambda e: mei_cnae.update(value=e.control.value or ""),
                width=_ONBOARDING_WIDTH,
            )

            def on_profile_pick(e):
                mei_operational.update(value=e.control.value or "on_demand")
                sync_profile_hint()
                app.page.update()

            def apply_cnae(_):
                suggested = suggest_from_cnae(mei_cnae["value"])
                mei_operational["value"] = suggested
                sync_profile_hint()
                refresh_body()
                app.page.update()

            body.content = ft.Column(
                [
                    title_text(t("onboarding.mei_profile_title"), size=22),
                    body_text(t("onboarding.mei_profile_body"), size=13),
                    cnae_input,
                    ft.TextButton(t("onboarding.suggest_cnae"), on_click=apply_cnae),
                    profile_radio_group(value=mei_operational["value"], on_change=on_profile_pick),
                    profile_hint,
                ],
                spacing=10,
                tight=True,
            )
        elif step_id == "data":
            sync_path_labels()
            body.content = ft.Column(
                [
                    title_text(t("onboarding.data_title"), size=22),
                    body_text(
                        t("onboarding.data_body", default_root=get_default_data_root()),
                        size=13,
                    ),
                    ft.Row([path_field], spacing=8),
                    db_label,
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                t("onboarding.pick_folder"),
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=_pick_data_folder,
                            ),
                            ft.TextButton(
                                t("onboarding.open_folder"),
                                on_click=lambda _: _open_folder(app),
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=12,
                tight=True,
            )
        elif step_id == "backup":
            backup_switch = ft.Switch(
                label=t("onboarding.backup_switch"),
                value=backup_on_close["value"],
                active_color=PERSONAL_ACCENT,
                on_change=lambda e: backup_on_close.update(value=bool(e.control.value)),
            )
            body.content = ft.Column(
                [
                    title_text(t("onboarding.backup_title"), size=22),
                    body_text(
                        t("onboarding.backup_body", backup_dir=get_default_backup_dir()),
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
                    title_text(t("onboarding.start_title"), size=22),
                    body_text(t("onboarding.start_body"), size=13),
                    ft.ElevatedButton(
                        t("onboarding.import_now"),
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda _: _finish(
                            app,
                            setup_mode["value"],
                            backup_on_close["value"],
                            demo=False,
                            import_now=True,
                            mei_operational=mei_operational["value"],
                            mei_cnae=mei_cnae["value"],
                            country=_country(),
                        ),
                        style=primary_button_style(bgcolor=PERSONAL_ACCENT),
                    ),
                    ft.OutlinedButton(
                        t("onboarding.explore_demo"),
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                        on_click=lambda _: _finish(
                            app,
                            setup_mode["value"],
                            backup_on_close["value"],
                            demo=True,
                            import_now=False,
                            mei_operational=mei_operational["value"],
                            mei_cnae=mei_cnae["value"],
                            country=_country(),
                        ),
                    ),
                    ft.TextButton(
                        t("onboarding.skip"),
                        on_click=lambda _: _finish(
                            app,
                            setup_mode["value"],
                            backup_on_close["value"],
                            demo=False,
                            import_now=False,
                            mei_operational=mei_operational["value"],
                            mei_cnae=mei_cnae["value"],
                            country=_country(),
                        ),
                    ),
                ],
                spacing=10,
                tight=True,
            )

        nav_row.controls = _nav_buttons(step["index"], setup_mode["value"], _country())

    async def _pick_data_folder(_):
        picked = await ft.FilePicker().get_directory_path(
            dialog_title=t("onboarding.folder_dialog"),
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
            app.show_snack(t("onboarding.folder_error", error=ex), success=False)

    def _nav_buttons(idx: int, mode: str, country_code: str) -> list[ft.Control]:
        flow = _step_flow(mode, country_code)
        buttons: list[ft.Control] = []
        if idx > 0:
            buttons.append(ft.TextButton(t("onboarding.back"), on_click=lambda _: _go(-1, mode)))
        buttons.append(ft.Container(expand=True))
        if idx < len(flow) - 1:
            buttons.append(
                ft.ElevatedButton(
                    t("onboarding.continue"),
                    on_click=lambda _: _go(1, mode),
                    style=primary_button_style(bgcolor=PERSONAL_ACCENT),
                )
            )
        return buttons

    def _go(delta: int, mode: str):
        flow = _step_flow(mode, _country())
        step["index"] = max(0, min(len(flow) - 1, step["index"] + delta))
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
        app.show_snack(t("onboarding.open_folder_error", error=ex), success=False)


def _finish(
    app: "OrcFinApp",
    mode: str,
    backup: bool,
    *,
    demo: bool,
    import_now: bool,
    mei_operational: str = "on_demand",
    mei_cnae: str = "",
    country: str = "BR",
):
    preset = COUNTRY_PRESETS.get(country) or COUNTRY_PRESETS["BR"]
    if not supports_mei(country) and mode in ("mei", "both"):
        mode = "personal"
    app.settings["country_profile"] = country
    app.settings["locale"] = preset["locale"]
    app.settings["currency"] = preset["currency"]
    app.settings["setup_mode"] = mode
    app.settings["backup_on_close"] = backup
    app.settings["backup_dir"] = str(get_default_backup_dir())
    if supports_mei(country) and mode in ("mei", "both"):
        app.settings["mei_operational_profile"] = mei_operational or "on_demand"
        app.settings["mei_cnae"] = (mei_cnae or "").strip()
    if mode == "mei":
        app.settings["app_mode"] = "mei"
    else:
        app.settings["app_mode"] = "personal"
    app.settings["onboarding_completed"] = True
    apply_from_settings(app.settings)
    save_settings(app.settings)
    app.complete_onboarding(use_demo=demo, open_import=import_now)
