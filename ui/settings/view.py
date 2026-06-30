"""Application settings — profiles, accounts, appearance, and system."""
from __future__ import annotations

import flet as ft

from core.db.repositories.categories import get_categories_for_mode
from core.db.repositories.profiles import get_all_profiles
from ui.settings.context import SettingsCtx
from ui.settings.helpers import title_text
from ui.settings import appearance, accounts, financial, system

class SettingsView:
    def __init__(self, app: "OrcFinApp"):
        self.ctx = SettingsCtx(
            app=app,
            profiles=get_all_profiles(),
            categories=get_categories_for_mode(app.is_mei_mode()),
        )

    def build(self) -> ft.Control:
        ctx = self.ctx
        sections = [
            appearance.build_appearance_section(ctx),
            accounts.build_profiles_section(ctx),
            accounts.build_categories_section(ctx),
            financial.build_goals_section(ctx),
            financial.build_net_worth_section(ctx),
            financial.build_budgets_section(ctx),
            financial.build_rules_section(ctx),
            system.build_backup_section(ctx),
            system.build_export_section(ctx),
            system.build_danger_zone_section(ctx),
            system.build_ai_section(ctx),
        ]
        return ft.Container(
            expand=True,
            content=ft.Column(
                [title_text("Configurações"), ft.Container(height=24)]
                + [s for sec in sections for s in (sec, ft.Container(height=24))][:-1],
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
            ),
        )
