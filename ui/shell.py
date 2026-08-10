"""Flet application shell — layout, chrome, and event handlers."""

import flet as ft
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from core.branding import APP_NAME, APP_NAME_MEI, APP_VERSION
from core.db.repositories.mei import get_mei_config, get_mei_profile
from core.db.repositories.profiles import get_all_profiles
from core.db.connection import get_connection
from core.db.schema import init_database
from core.i18n import apply_from_settings, supports_mei, t
from core.settings_store import load_settings, save_settings, reset_preferences_after_data_wipe
from core.backup import create_backup, maybe_auto_backup, prune_backups

from ui.mei.constants import MEI_ACCENT, PERSONAL_ACCENT
from ui.theme import active as theme_colors, modal_dialog_kwargs, segmented_button_style, set_active
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
        self._open_dialogs: list[ft.AlertDialog] = []
        self.settings = load_settings()
        apply_from_settings(self.settings)
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

    def _mei_available(self) -> bool:
        return supports_mei(self.settings.get("country_profile"))

    def _finish_startup(self) -> None:
        self._run_auto_backup_if_due()
        # Non-BR profiles never open the MEI shell (module is Brazil-only).
        if not self._mei_available() and (
            self.is_mei_mode() or self.settings.get("setup_mode") in ("mei", "both")
        ):
            self.settings["app_mode"] = "personal"
            if self.settings.get("setup_mode") in ("mei", "both"):
                self.settings["setup_mode"] = "personal"
            self.state.app_mode = "personal"
            save_settings(self.settings)
        self._build_ui()
        self._setup_backup_on_close()
        if self._mei_available() and (
            self.settings.get("setup_mode") == "mei" or self.is_mei_mode()
        ):
            self.enter_mei_shell(home=True, initial=True)
        else:
            switch_view(self, self.current_view_index)
        self._maybe_prompt_recurrences()
        self._start_portfolio_quote_scheduler()
        self._center_window()

    def _start_portfolio_quote_scheduler(self) -> None:
        from core.services.portfolio_quotes_scheduler import start_portfolio_quote_scheduler

        start_portfolio_quote_scheduler(self)

    def complete_onboarding(self, *, use_demo: bool, open_import: bool) -> None:
        personal_demo = mei_demo = 0
        if use_demo:
            from core.demo_data import seed_demo_onboarding

            personal_demo, mei_demo = seed_demo_onboarding(self.settings)
            if mei_demo:
                save_settings(self.settings)
        self.profiles = get_all_profiles()
        self.state = AppState.from_settings(self.settings)
        self.state.on_settings_changed = lambda: save_settings(self.settings)
        self.page.clean()
        self._restore_main_window()
        self._finish_startup()
        self.page.update()
        if personal_demo or mei_demo:
            parts: list[str] = []
            if personal_demo:
                parts.append(t("shell.demo_personal", count=personal_demo))
            if mei_demo:
                parts.append(t("shell.demo_mei", count=mei_demo))
            self.show_snack(t("shell.demo_added", parts=", ".join(parts)))
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
        self.page.window.width = 580
        self.page.window.height = 700
        self.page.window.min_width = 520
        self.page.window.min_height = 520

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
        self.page.title = f"{APP_TITLE} v{APP_VERSION}"
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
        if hasattr(self, "context_chip"):
            self.context_chip.bgcolor = c.surface_alt
            self.context_chip.border = ft.Border.all(1, c.border)
            self.context_chip_text.color = c.text_primary
        if hasattr(self, "mode_toggle"):
            seg_style = segmented_button_style(accent=accent)
            self.mode_toggle.style = seg_style
            self.view_mode_toggle.style = seg_style
        if hasattr(self, "page") and self.page.width and self.page.width < 1100 and hasattr(self, "nav_rail"):
            self.nav_rail.extended = False
            self.nav_rail.label_type = ft.NavigationRailLabelType.SELECTED
        elif hasattr(self, "nav_rail"):
            self.nav_rail.extended = True
            self.nav_rail.label_type = ft.NavigationRailLabelType.ALL

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
                self.subtitle_text.value = t("app.subtitle")
                self.subtitle_text.visible = True
        else:
            self.title_text.value = APP_TITLE
            self.subtitle_text.value = t("app.subtitle")
            self.subtitle_text.visible = True
        self._update_context_chip()

    def _update_context_chip(self):
        if not hasattr(self, "context_chip_text"):
            return
        from ui.personal.period_filter import period_label

        period = period_label(self.filter_year, self.filter_month)
        if self.is_mei_mode():
            label = t("shell.context_mei", period=period)
        else:
            mode = t("shell.mode_consolidated") if self.is_consolidated else t("shell.mode_individual")
            if self.is_consolidated:
                base = t("shell.mode_consolidated")
            else:
                pid = self.ensure_individual_profile()
                profile = next((p for p in self.profiles if p.id == pid), None) if pid else None
                base = profile.name if profile else t("shell.mode_individual")
            label = t("shell.context_personal", base=base, mode=mode, period=period)
        self.context_chip_text.value = label
        self.context_chip.visible = True

    def _build_ui(self):
        self.profile_dropdown = ft.Dropdown(
            width=200,
            hint_text=t("shell.profile_hint"),
            value=str(self.selected_profile_id) if self.selected_profile_id else None,
            options=[ft.dropdown.Option(str(p.id), p.name) for p in self.profiles],
            on_select=self._on_profile_change,
        )

        seg_style = segmented_button_style(accent=self._accent())
        self.mode_toggle = ft.SegmentedButton(
            selected=["mei" if self.is_mei_mode() else "personal"],
            on_change=self._on_app_mode_change,
            style=seg_style,
            visible=self._mei_available(),
            segments=[
                ft.Segment(value="personal", label=ft.Text(t("shell.personal"), size=11), icon=ft.Icons.PERSON),
                ft.Segment(value="mei", label=ft.Text(t("shell.mei"), size=11), icon=ft.Icons.BUSINESS),
            ],
        )

        self.view_mode_toggle = ft.SegmentedButton(
            selected=["consolidated" if self.is_consolidated else "individual"],
            on_change=self._on_view_mode_change,
            style=seg_style,
            segments=[
                ft.Segment(value="consolidated", label=ft.Text(t("shell.consolidated"), size=11), icon=ft.Icons.PEOPLE),
                ft.Segment(value="individual", label=ft.Text(t("shell.individual"), size=11), icon=ft.Icons.PERSON),
            ],
        )

        self.title_text = ft.Text(APP_TITLE, size=22, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(t("app.subtitle"), size=11, visible=True)
        self.logo_image = ft.Image(
            src="/orcfin_logo.png",
            width=40,
            height=40,
            fit=ft.BoxFit.CONTAIN,
            border_radius=8,
        )

        c0 = theme_colors()
        self.context_chip_text = ft.Text("", size=12, color=c0.text_primary, weight=ft.FontWeight.W_500)
        self.context_chip = ft.Container(
            content=self.context_chip_text,
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=20,
            bgcolor=c0.surface_alt,
            border=ft.Border.all(1, c0.border),
            visible=False,
        )

        self.personal_actions = ft.Row(
            [
                ft.Container(content=self.profile_dropdown),
                ft.Text(t("shell.view_label"), size=12, color=c0.text_muted),
                self.view_mode_toggle,
            ],
            spacing=8,
        )

        self.mei_actions = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.EDIT,
                    tooltip=t("shell.edit_mei"),
                    icon_color=MEI_ACCENT,
                    on_click=lambda _: open_edit_config(self),
                ),
                ft.IconButton(
                    ft.Icons.SETTINGS,
                    tooltip=t("shell.settings"),
                    icon_color=c0.text_muted,
                    on_click=lambda _: self._open_settings_from_mei(),
                ),
            ],
            spacing=0,
        )

        self.appbar_actions_row = ft.Row(
            [self.context_chip, self.mode_toggle, self.personal_actions, self.mei_actions],
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
            min_width=72,
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

        self._toast_text = ft.Text("", size=13, text_align=ft.TextAlign.CENTER)
        self._toast = ft.Container(
            content=self._toast_text,
            visible=False,
            padding=ft.Padding(16, 12, 16, 12),
            border_radius=8,
            bottom=20,
            left=20,
            right=20,
        )
        self.page.overlay.append(self._toast)

        self._sync_shell_chrome()

    def _shell_divider(self) -> ft.VerticalDivider:
        return ft.VerticalDivider(width=1, color=theme_colors().divider)

    def _sync_shell_chrome(self):
        is_mei = self.is_mei_mode() and self._mei_available()
        self.mode_toggle.visible = self._mei_available()
        self.mode_toggle.selected = ["mei" if is_mei else "personal"]
        self.personal_actions.visible = not is_mei
        self.mei_actions.visible = is_mei
        self.profile_dropdown.visible = not is_mei
        self._update_appbar_title()
        self._apply_shell_theme()

    def _mei_operational_profile(self) -> str | None:
        mei = get_mei_profile()
        if mei:
            cfg = get_mei_config(mei.id)
            if cfg:
                return cfg.operational_profile
        raw = self.settings.get("mei_operational_profile")
        return str(raw) if raw else None

    def enter_mei_shell(self, home: bool = False, initial: bool = False):
        if not self._mei_available():
            self.enter_personal_shell()
            return
        self.state.enter_mei_shell(home=home)
        self.nav_rail.destinations = mei_destinations(self._mei_operational_profile())
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

    def switch_mei_tab_label(self, label: str):
        from ui.mei_router import mei_tab_index

        self.switch_mei_tab(mei_tab_index(self._mei_operational_profile(), label))

    def _open_settings_from_mei(self):
        from ui.settings import SettingsView

        settings_body = SettingsView(self).build()
        c = theme_colors()
        dialog = ft.AlertDialog(
            title=ft.Text(t("shell.settings"), size=18, weight=ft.FontWeight.W_600, color=c.text_primary),
            content=ft.Container(content=settings_body, width=860, height=580, padding=8),
            actions=[ft.TextButton(t("common.close"), on_click=lambda _: self.close_modal())],
            actions_alignment=ft.MainAxisAlignment.END,
            **modal_dialog_kwargs(modal=True),
        )
        self._open_dialogs.append(dialog)
        self.page.show_dialog(dialog)

    def _on_app_mode_change(self, e: ft.ControlEvent):
        selected = next(iter(e.control.selected), "personal")
        if selected == "mei" and self._mei_available():
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
        self._save_settings()
        self._update_context_chip()
        switch_view(self, self.current_view_index)

    def _on_nav_change(self, e: ft.ControlEvent):
        switch_view(self, e.control.selected_index)

    def refresh_current_view(self):
        self._refresh_profiles()
        self._update_context_chip()
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

    def _close_dialog_stack(self, *, all_dialogs: bool) -> None:
        if not self._open_dialogs:
            return
        if all_dialogs:
            for dlg in self._open_dialogs:
                dlg.open = False
            self._open_dialogs.clear()
            return
        dlg = self._open_dialogs.pop()
        dlg.open = False

    def _dismiss_all_dialogs(self) -> None:
        self._close_dialog_stack(all_dialogs=True)

    def clean_transient_ui(self) -> None:
        if getattr(self, "_toast", None):
            self._toast.visible = False
        for ctrl in list(self.page.overlay):
            if isinstance(ctrl, (ft.SnackBar, ft.DatePicker)):
                self.page.overlay.remove(ctrl)
        self._dismiss_all_dialogs()

    def show_snack(self, message: str, success: bool = True):
        self.clean_transient_ui()
        c = theme_colors()
        self._toast_text.value = message
        self._toast_text.color = c.text_primary
        self._toast.bgcolor = self._accent() if success else c.snack_error
        self._toast.visible = True
        self.page.update()

        async def _hide_toast():
            import asyncio

            await asyncio.sleep(2.5)
            self._toast.visible = False
            self.page.update()

        self.page.run_task(_hide_toast)

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
            title=ft.Text(title, size=18, weight=ft.FontWeight.W_600, color=c.text_primary) if title else None,
            content=content,
            actions_alignment=ft.MainAxisAlignment.END,
            **modal_dialog_kwargs(modal=True),
        )
        self._open_dialogs.append(dialog)
        self.page.show_dialog(dialog)

    def close_modal(self, *, all_dialogs: bool = False) -> None:
        """Close the top dialog, or the full stack when all_dialogs=True."""
        self._close_dialog_stack(all_dialogs=all_dialogs)
        self.page.update()

    def close_all_modals(self) -> None:
        self.close_modal(all_dialogs=True)

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
            "• "
            + t(
                "shell.recurrence_item",
                description=r["description"],
                amount=r["average_amount"],
                months=r["distinct_months"],
            )
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
            self.current_view_index = 4
            switch_view(self, 4)

        self.show_modal(
            ft.Column(
                [
                    ft.Text(
                        t("shell.recurrence_body"),
                        size=13,
                        color=theme_colors().text_secondary,
                    ),
                    ft.Text(lines, size=12, color=theme_colors().text_primary),
                    ft.Row(
                        [
                            ft.TextButton(t("common.later"), on_click=dismiss),
                            ft.ElevatedButton(t("shell.recurrence_open"), on_click=open_reports),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            title=t("shell.recurrence_title"),
        )