"""MEI profile setup wizard."""

from __future__ import annotations

import flet as ft

from core.branding import APP_SUBTITLE
from core.mei_operational import suggest_profile
from core.services.mei_service import create_mei_profile
from ui.mei.components import mei_card, mei_heading, mei_text, mei_title, modal_dropdown, modal_field
from ui.mei.constants import ACTIVITY_LABELS, MEI_ACCENT
from ui.mei.operational_profile import cnae_field, profile_dropdown, profile_hint_text, suggest_from_cnae


def build_setup(app: "OrcFinApp") -> ft.Control:
    name_f = modal_field(label="Nome do perfil", value="MEI", width=400)
    razao_f = modal_field(label="Razão social", width=400)
    cnpj_f = modal_field(label="CNPJ", width=400)
    activity_dd = modal_dropdown(
        label="Natureza da atividade (DAS)",
        width=400,
        value="servico",
        options=[ft.dropdown.Option(k, v) for k, v in ACTIVITY_LABELS.items()],
    )
    cnae_f = cnae_field(value=app.settings.get("mei_cnae") or "", width=400)
    profile_dd = profile_dropdown(value=app.settings.get("mei_operational_profile"), width=400)
    hint = profile_hint_text(profile_dd.value)

    def on_cnae_change(e):
        suggested = suggest_from_cnae(e.control.value or "")
        profile_dd.value = suggested
        hint.value = profile_hint_text(suggested).value
        if app.page:
            app.page.update()

    def on_profile_change(e):
        hint.value = profile_hint_text(e.control.value).value
        if app.page:
            app.page.update()

    cnae_f.on_change = on_cnae_change
    profile_dd.on_change = on_profile_change

    if cnae_f.value:
        profile_dd.value = suggest_profile(cnae_f.value)
        hint.value = profile_hint_text(profile_dd.value).value

    def create(_):
        if not razao_f.value or not cnpj_f.value:
            app.show_snack("Preencha razão social e CNPJ", success=False)
            return
        operational = profile_dd.value or app.settings.get("mei_operational_profile") or "on_demand"
        cnae = (cnae_f.value or "").strip() or None
        profile, _ = create_mei_profile(
            name=name_f.value or "MEI",
            razao_social=razao_f.value,
            cnpj=cnpj_f.value,
            activity_type=activity_dd.value or "servico",
            operational_profile=operational,
            cnae=cnae,
        )
        app.settings["mei_profile_id"] = profile.id
        app.settings["mei_operational_profile"] = operational
        app.settings["mei_cnae"] = cnae or ""
        app.settings["app_mode"] = "mei"
        app.selected_profile_id = profile.id
        app.is_consolidated = False
        app._save_settings()
        app.enter_mei_shell(home=True)
        app.show_snack("Perfil MEI criado!")

    return ft.Column(
        [
            mei_title("Bem-vindo ao OrcFin MEI"),
            mei_text(APP_SUBTITLE, size=13, muted=True),
            mei_text(
                "Configure seu CNPJ para controlar DAS, limite de faturamento, "
                "notas fiscais e resultado do negócio, separado das finanças pessoais.",
                size=14,
            ),
            ft.Container(height=24),
            mei_card(
                ft.Column(
                    [
                        mei_heading("Criar perfil MEI"),
                        name_f,
                        razao_f,
                        cnpj_f,
                        activity_dd,
                        cnae_f,
                        profile_dd,
                        hint,
                        ft.ElevatedButton(
                            "Ativar modo MEI",
                            icon=ft.Icons.BUSINESS,
                            on_click=create,
                            style=ft.ButtonStyle(bgcolor=MEI_ACCENT, color=ft.Colors.WHITE),
                        ),
                    ],
                    spacing=12,
                ),
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )