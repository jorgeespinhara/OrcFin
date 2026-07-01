"""MEI profile setup wizard."""

from __future__ import annotations

import flet as ft

from core.branding import APP_SUBTITLE
from core.services.mei_service import create_mei_profile
from ui.mei.components import mei_card, mei_heading, mei_text, mei_title, modal_dropdown, modal_field
from ui.mei.constants import ACTIVITY_LABELS, MEI_ACCENT


def build_setup(app: "OrcFinApp") -> ft.Control:
    name_f = modal_field(label="Nome do perfil", value="MEI", width=400)
    razao_f = modal_field(label="Razão social", width=400)
    cnpj_f = modal_field(label="CNPJ", width=400)
    activity_dd = modal_dropdown(
        label="Natureza da atividade",
        width=400,
        value="servico",
        options=[ft.dropdown.Option(k, v) for k, v in ACTIVITY_LABELS.items()],
    )

    def create(_):
        if not razao_f.value or not cnpj_f.value:
            app.show_snack("Preencha razão social e CNPJ", success=False)
            return
        profile, _ = create_mei_profile(
            name=name_f.value or "MEI",
            razao_social=razao_f.value,
            cnpj=cnpj_f.value,
            activity_type=activity_dd.value or "servico",
        )
        app.settings["mei_profile_id"] = profile.id
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