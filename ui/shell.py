"""Flet application shell — layout, chrome, and event handlers."""

import flet as ft
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from core.branding import APP_NAME, APP_NAME_MEI, APP_SUBTITLE
from core.db.repositories.mei import get_mei_config, get_mei_profile
from core.db.repositories.profiles import get_all_profiles
from core.db.connection import get_connection
from core.db.schema import init_database
from core.settings_store import load_settings, save_settings, reset_preferences_after_data_wipe
from core.backup import create_backup, maybe_auto_backup, prune_backups

from ui.mei.constants import MEI_ACCENT, PERSONAL_ACCENT
from ui.theme import active as theme_colors, set_active
from ui.mei.actions import open_edit_config
from ui.state import AppState
from ui.state.proxy import StateProxyMixin
from ui.router import personal_destinations, switch_view
from ui.mei_router import mei_destinations


APP_TITLE = APP_NAME
_ICON_PATH = Path(__file__).parent.parent / "assets" / "orcfin.ico"


class OrcFinApp(StateProxyMixin):
    """Flet shell — state in AppState, navigation in router."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.settings = load_settings()
        self.state = AppState.from_settings(self.settings)
        self.state.on_settings_changed = lambda: save_settings(self.settings)

        init_database()
        self.profiles = get_all_profiles()
        self._setup_theme()

        if self._needs_onboarding():
            self._build_onboarding_ui()
            self._setup_backup_on_close()
            return

        self._finish_startup()

    def _needs_onboarding(self) -> bool:
        if self.settings.get("onboarding_completed"):
            return False
        conn = get_connection()
        try:
            tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            if tx_count > 0 or self.settings.get("mei_profile_id") or self.settings.get("last_backup_at"):
                self.settings["onboarding_completed"] = True
                save_settings(self.settings)
                return False
        finally:
            conn.close()
        return True

    def _finish_startup(self) -> None:
        self._run_auto_backup_if_due()
        self._build_ui()
        self._setup_backup_on_close()
        if self.settings.get("setup_mode") == "mei" or self.is_mei_mode():
            self.enter_mei_shell(home=True, initial=True)
        else:
            switch_view(self, self.current_view_index)
        self._maybe_prompt_recurrences()
        self._center_window()

    def complete_onboarding(self, *, use_demo: bool, open_import: bool) -> None:
        if use_demo:
            from core.demo_data import seed_demo_transactions

            count = seed_demo_transactions()
            if count:
                self.show_snack(f"Dados fictícios adicionados ({count} lançamentos)")
        self.profiles = get_all_profiles()
        self.state = AppState.from_settings(self.settings)
        self.state.on_settings_changed = lambda: save_settings(self.settings)
        self.page.clean()
        self._restore_main_window()
        self._finish_startup()
        self.page.update()
        if open_import:
            from ui.import_flow import open_import_flow

            open_import_flow(self)

    def _center_window(self) -> None:
        async def _do_center():
            await self.page.window.wait_until_ready_to_show()
            await self.page.window.center()

        self.page.run_task(_do_center)

    def _build_onboarding_ui(self) -> None:
        from ui.onboarding import build_onboarding

        self._onboarding_window_state = (
            self.page.window.width,
            self.page.window.height,
            self.page.window.min_width,
            self.page.window.min_height,
        )
        self.page.window.width = 520
        self.page.window.height = 580
        self.page.window.min_width = 480
        self.page.window.min_height = 420

        c = theme_colors()
        self.page.add(
            ft.Container(
                content=build_onboarding(self),
                expand=True,
                bgcolor=c.content_bg,
            )
        )
        self._center_window()

    def _restore_main_window(self) -> None:
        state = getattr(self, "_onboarding_window_state", None)
        if not state:
            return
        width, height, min_width, min_height = state
        self.page.window.width = width
        self.page.window.height = height
        self.page.window.min_width = min_width
        self.page.window.min_height = min_height

    def _save_settings(self) -> None:
        self.state.save_settings()

    def _accent(self) -> str:
        return MEI_ACCENT if self.is_mei_mode() else PERSONAL_ACCENT

    def _theme_mode_name(self) -> str:
        mode = self.settings.get("theme_mode", "dark")
        return mode if mode in ("dark", "light") else "dark"

    def _setup_theme(self):
        self.page.padding = 0
        self.page.window.width = 1280
        self.page.window.height = 800
        self.page.window.min_width = 1024
        self.page.window.min_height = 700
        self.page.title = f"{APP_TITLE}: {APP_SUBTITLE}"
        if _ICON_PATH.exists():
            self.page.window.icon = str(_ICON_PATH)
        self._apply_shell_theme()

    def _apply_shell_theme(self):
        mode = self._theme_mode_name()
        set_active(mode)
        c = theme_colors()
        accent = self._accent()
        is_light = mode == "light"
        self.page.theme_mode = ft.ThemeMode.LIGHT if is_light else ft.ThemeMode.DARK
        base_theme = ft.Theme(
            color_scheme_seed=accent,
            visual_density=ft.VisualDensity.COMFORTABLE,
        )
        self.page.theme = base_theme
        self.page.dark_theme = base_theme
        self.page.bgcolor = c.page_bg
        if hasattr(self, "nav_rail"):
            self.nav_rail.indicator_color = accent
            self.nav_rail.bgcolor = c.nav_bg if self.app_mode == "personal" else c.nav_bg_mei
        if hasattr(self, "appbar"):
            self.appbar.bgcolor = c.appbar_bg if self.app_mode == "personal" else c.appbar_bg_mei
        if hasattr(self, "content_area"):
            self.content_area.bgcolor = c.content_bg if self.app_mode == "personal" else c.content_bg_mei
        if hasattr(self, "title_text"):
            self.title_text.color = c.text_primary
        if hasattr(self, "subtitle_text"):
            self.subtitle_text.color = c.text_muted
        if hasattr(self, "personal_actions"):
            for ctrl in self.personal_actions.controls:
                if isinstance(ctrl, ft.Text):
                    ctrl.color = c.text_muted

    def apply_theme_mode(self, mode: str) -> None:
        if mode not in ("dark", "light"):
            return
        self.settings["theme_mode"] = mode
        self._save_settings()
        self._apply_shell_theme()
        self.refresh_current_view()
        self.page.update()

    def _run_auto_backup_if_due(self) -> None:
        try:
            if maybe_auto_backup(self.settings):
                save_settings(self.settings)
        except Exception:
            logger.warning("Auto-backup on startup failed", exc_info=True)

    def _setup_backup_on_close(self):
        def on_disconnect(_):
            if self.settings.get("backup_on_close"):
                try:
                    dest = Path(self.settings["backup_dir"]) if self.settings.get("backup_dir") else None
                    create_backup(dest)
                    prune_backups(
                        dest,
                        int(self.settings.get("backup_retention_count") or 7),
                    )
                    self.settings["last_backup_at"] = datetime.now().isoformat(timespec="seconds")
                    save_settings(self.settings)
                except Exception:
                    logger.warning("Backup on close failed", exc_info=True)
        self.page.on_disconnect = on_disconnect

    def _update_appbar_title(self):
        if self.is_mei_mode():
            mei = get_mei_profile()
            cfg = get_mei_config(mei.id) if mei else None
            if cfg:
                self.title_text.value = APP_NAME_MEI
                self.subtitle_text.value = f"{cfg.razao_social} • {cfg.cnpj}"
                self.subtitle_text.visible = True
            else:
                self.title_text.value = APP_NAME_MEI
                self.subtitle_text.value = APP_SUBTITLE
                self.subtitle_text.visible = True
        else:
            self.title_text.value = APP_TITLE
            self.subtitle_text.value = APP_SUBTITLE
            self.subtitle_text.visible = True

    def _build_ui(self):
        self.profile_dropdown = ft.Dropdown(
            width=200,
            hint_text="Perfil",
            value=str(self.selected_profile_id) if self.selected_profile_id else None,
            options=[ft.dropdown.Option(str(p.id), p.name) for p in self.profiles],
            on_select=self._on_profile_change,
        )

        self.mode_toggle = ft.SegmentedButton(
            selected=["mei" if self.is_mei_mode() else "personal"],
            on_change=self._on_app_mode_change,
            segments=[
                ft.Segment(value="personal", label=ft.Text("Pessoal", size=11), icon=ft.Icons.PERSON),
                ft.Segment(value="mei", label=ft.Text("MEI", size=11), icon=ft.Icons.BUSINESS),
            ],
        )

        self.view_mode_toggle = ft.SegmentedButton(
            selected=["consolidated" if self.is_consolidated else "individual"],
            on_change=self._on_view_mode_change,
            segments=[
                ft.Segment(value="consolidated", label=ft.Text("Consolidada", size=11), icon=ft.Icons.PEOPLE),
                ft.Segment(value="individual", label=ft.Text("Individual", size=11), icon=ft.Icons.PERSON),
            ],
        )

        self.title_text = ft.Text(APP_TITLE, size=22, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(APP_SUBTITLE, size=11, visible=True)
        self.logo_image = ft.Image(
            src="/orcfin_logo.png",
            width=40,
            height=40,
            fit=ft.BoxFit.CONTAIN,
            border_radius=8,
        )

        self.personal_actions = ft.Row(
            [
                ft.Container(content=self.profile_dropdown),
                ft.Text("Visão:", size=12, color=theme_colors().text_muted),
                self.view_mode_toggle,
            ],
            spacing=8,
        )

        self.mei_actions = ft.Row(
            [
                ft.IconButton(ft.Icons.EDIT, tooltip="Editar perfil MEI", icon_color=MEI_ACCENT, on_click=lambda _: open_edit_config(self)),
                ft.IconButton(ft.Icons.SETTINGS, tooltip="Configurações", icon_color=ft.Colors.GREY_400, on_click=lambda _: self._open_settings_from_mei()),
            ],
            spacing=0,
        )

        self.appbar_actions_row = ft.Row(
            [self.mode_toggle, self.personal_actions, self.mei_actions],
            spacing=12,
        )

        self.appbar = ft.AppBar(
            title=ft.Row(
                [
                    self.logo_image,
                    ft.Column([self.title_text, self.subtitle_text], spacing=0, tight=True),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            center_title=False,
            actions=[ft.Container(content=self.appbar_actions_row, padding=ft.Padding(right=16))],
        )

        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            extended=True,
            min_extended_width=200,
            indicator_color=PERSONAL_ACCENT,
            destinations=personal_destinations(),
            on_change=self._on_nav_change,
        )

        self.content_area = ft.Container(expand=True, padding=24)

        self.page.add(
            self.appbar,
            ft.Row(
                [self.nav_rail, self._shell_divider(), self.content_area],
                expand=True,
                spacing=0,
            ),
        )

        self._sync_shell_chrome()

    def _shell_divider(self) -> ft.VerticalDivider:
        return ft.VerticalDivider(width=1, color=theme_colors().divider)

    def _sync_shell_chrome(self):
        is_mei = self.is_mei_mode()
        self.mode_toggle.selected = ["mei" if is_mei else "personal"]
        self.personal_actions.visible = not is_mei
        self.mei_actions.visible = is_mei
        self.profile_dropdown.visible = not is_mei
        self._update_appbar_title()
        self._apply_shell_theme()

    def enter_mei_shell(self, home: bool = False, initial: bool = False):
        self.state.enter_mei_shell(home=home)
        self.nav_rail.destinations = mei_destinations()
        self.nav_rail.selected_index = self.mei_view_index
        self._sync_shell_chrome()
        if not initial:
            self._save_settings()
        switch_view(self, self.mei_view_index)

    def enter_personal_shell(self):
        self.state.enter_personal_shell()
        self.nav_rail.destinations = personal_destinations()
        self.nav_rail.selected_index = self.current_view_index
        self._sync_shell_chrome()
        self._save_settings()
        switch_view(self, self.current_view_index)

    def switch_mei_tab(self, index: int):
        if not self.is_mei_mode():
            self.enter_mei_shell()
        self.mei_view_index = index
        switch_view(self, index)

    def _open_settings_from_mei(self):
        from ui.settings import SettingsView

        settings_body = SettingsView(self).build()
        c = theme_colors()
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Configurações", size=18, weight=ft.FontWeight.W_600, color=c.text_primary),
            content=ft.Container(content=settings_body, width=720, height=520, padding=0),
            actions=[ft.TextButton("Fechar", on_click=lambda _: self.close_modal())],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=c.modal_bg,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.page.show_dialog(dialog)

    def _on_app_mode_change(self, e: ft.ControlEvent):
        selected = next(iter(e.control.selected), "personal")
        if selected == "mei":
            self.enter_mei_shell(home=True)
            self._save_settings()
        else:
            self.enter_personal_shell()

    def _on_view_mode_change(self, e: ft.ControlEvent):
        if self.is_mei_mode():
            return
        selected_value = next(iter(e.control.selected), "consolidated")
        self.is_consolidated = selected_value == "consolidated"
        if not self.is_consolidated:
            self.ensure_individual_profile()
        switch_view(self, self.current_view_index)

    def _on_nav_change(self, e: ft.ControlEvent):
        switch_view(self, e.control.selected_index)

    def refresh_current_view(self):
        self._refresh_profiles()
        switch_view(self, self.active_view_index())

    def _reload_shell_after_reset(self, settings: dict):
        self.settings = settings
        self.state.reset_after_wipe(settings)
        if hasattr(self, "_import_preferred_card_id"):
            self._import_preferred_card_id = None
        self.profiles = get_all_profiles()
        self._refresh_profiles()
        self.enter_personal_shell()
        self.page.update()

    def apply_financial_reset(self):
        self._reload_shell_after_reset(reset_preferences_after_data_wipe())

    def apply_clean_install_reset(self):
        from core.settings_store import load_settings

        self.settings = load_settings()
        self.state.reset_after_wipe(self.settings)
        if hasattr(self, "_import_preferred_card_id"):
            self._import_preferred_card_id = None
        self.page.clean()
        self._setup_theme()
        if self._needs_onboarding():
            self._build_onboarding_ui()
            self.page.update()
            return
        self.profiles = get_all_profiles()
        self._finish_startup()
        self.page.update()

    def _refresh_profiles(self):
        self.profiles = get_all_profiles()
        self.profile_dropdown.options = [ft.dropdown.Option(str(p.id), p.name) for p in self.profiles]
        if not self.is_mei_mode():
            if not self.is_consolidated:
                self.ensure_individual_profile()
            elif self.selected_profile_id and not any(p.id == self.selected_profile_id for p in self.profiles):
                self.selected_profile_id = self.profiles[0].id if self.profiles else None
                self._save_settings()
        self.profile_dropdown.value = str(self.selected_profile_id) if self.selected_profile_id else None
        self._update_appbar_title()

    def show_snack(self, message: str, success: bool = True):
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=self._accent() if success else theme_colors().snack_error,
                duration=ft.Duration(milliseconds=2500),
            )
        )

    def _on_profile_change(self, e: ft.ControlEvent):
        try:
            self.selected_profile_id = int(e.control.value) if e.control.value else None
        except (TypeError, ValueError):
            self.selected_profile_id = None
        self._save_settings()
        self.refresh_current_view()

    def show_modal(self, content: ft.Control, title: str = ""):
        c = theme_colors()
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=18, weight=ft.FontWeight.W_600, color=c.text_primary) if title else None,
            content=content,
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=c.modal_bg,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.page.show_dialog(dialog)

    def close_modal(self):
        self.page.pop_dialog()

    def _maybe_prompt_recurrences(self):
        if self.is_mei_mode():
            return
        if self.settings.get("recurrence_prompt_dismissed"):
            return

        from core.engine.recurrence_detection import should_prompt_recurrence_review, detect_recurring_transactions

        profile_id = self.get_view_profile_id()
        consolidated = self.is_consolidated
        if not should_prompt_recurrence_review(profile_id, consolidated):
            return

        recurrences = detect_recurring_transactions(profile_id, consolidated)[:5]
        lines = "\n".join(
            f"• {r['description'][:35]}: {r['average_amount']} ({r['distinct_months']} meses)"
            for r in recurrences
        )

        def dismiss(_):
            self.settings["recurrence_prompt_dismissed"] = True
            self._save_settings()
            self.close_modal()

        def open_reports(_):
            self.settings["recurrence_prompt_dismissed"] = True
            self._save_settings()
            self.close_modal()
            self.current_view_index = 3
            switch_view(self, 3)

        self.show_modal(
            ft.Column(
                [
                    ft.Text(
                        "Detectamos possíveis recorrências nos seus lançamentos (≥90 dias de histórico):",
                        size=13,
                        color=ft.Colors.GREY_300,
                    ),
                    ft.Text(lines, size=12, color=ft.Colors.WHITE),
                    ft.Row(
                        [
                            ft.TextButton("Depois", on_click=dismiss),
                            ft.ElevatedButton("Ver em Relatórios", on_click=open_reports),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title="Recorrências detectadas",
        )