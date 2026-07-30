"""AI financial analysis panel."""

from __future__ import annotations

import flet as ft

from core.ai_gateway import PROVIDERS, get_financial_insights, provider_is_configured
from core.engine.reporting import generate_ai_context
from core.network_policy import BLOCKED_MESSAGE, external_calls_allowed
from ui.theme import active as theme_colors, danger_button_style, primary_button_style


def build_ai_section(view) -> ft.Container:
    c = theme_colors()
    last_provider = {"key": None}

    view.ai_output = ft.Text(
        "Clique em um dos botões abaixo para gerar análises com base nos seus totais agregados.",
        size=13,
        color=c.text_secondary,
    )
    view.loading_indicator = ft.ProgressRing(visible=False, width=20, height=20, color=c.accent)

    action_row = ft.Row(spacing=8, visible=False)

    def _set_actions_visible(visible: bool):
        action_row.visible = visible

    def _execute_ai(provider_key: str):
        meta = PROVIDERS.get(provider_key, {})
        provider_name = meta.get("name", provider_key)
        last_provider["key"] = provider_key

        view.loading_indicator.visible = True
        _set_actions_visible(False)
        view.ai_output.value = f"Consultando {provider_name}... Isso pode levar alguns segundos."
        view.app.page.update()

        try:
            result = get_financial_insights(
                provider=provider_key,
                settings=view.app.settings,
                profile_id=view.app.get_view_profile_id(),
                consolidated=view.app.is_consolidated,
                use_fallback_on_error=False,
            )
            if result.error and result.insight is None:
                view.ai_output.value = f"Não foi possível usar {provider_name}.\n\n{result.error}"
                view.app.show_snack(result.error, success=False)
                return

            insight = result.insight
            if result.error and result.used_fallback:
                view.ai_output.value = (
                    f"Não foi possível usar {provider_name}.\n\n{result.error}\n\n"
                    "Análise local (offline):\n" + insight.summary
                )
                view.app.show_snack(result.error, success=False)
                _set_actions_visible(True)
                return

            parts = [f"[{insight.provider} · {insight.model}]\n\n", insight.summary]
            if insight.predictions:
                parts.append("\n\nPrevisões:\n• " + "\n• ".join(insight.predictions))
            if insight.cost_reduction_tips:
                parts.append("\n\nDicas de economia:\n• " + "\n• ".join(insight.cost_reduction_tips))
            if insight.general_advice and insight.general_advice != insight.summary:
                parts.append(f"\n\n{insight.general_advice}")
            if result.from_cache:
                parts.append("\n\n(Resposta recuperada do cache local.)")
            view.ai_output.value = "".join(parts)
            _set_actions_visible(True)
            view.app.show_snack(f"Análise de {provider_name} concluída.")
        except Exception as ex:
            view.ai_output.value = f"Erro ao consultar {provider_name}: {ex}"
            view.app.show_snack(f"Erro: {ex}", success=False)
        finally:
            view.loading_indicator.visible = False
            view.app.page.update()

    async def copy_output(_):
        text = view.ai_output.value or ""
        await view.app.page.clipboard.set(text)
        view.app.show_snack("Análise copiada.")

    def regenerate(_):
        key = last_provider["key"]
        if key:
            _execute_ai(key)

    action_row.controls = [
        ft.OutlinedButton("Copiar", icon=ft.Icons.CONTENT_COPY, on_click=copy_output),
        ft.OutlinedButton("Regenerar", icon=ft.Icons.REFRESH, on_click=regenerate),
    ]

    def _show_payload_preview(provider_key: str, context: str):
        meta = PROVIDERS.get(provider_key, {})
        provider_name = meta.get("name", provider_key)
        preview_field = ft.TextField(
            value=context,
            multiline=True,
            read_only=True,
            min_lines=12,
            max_lines=16,
            expand=True,
            text_size=12,
        )

        async def copy_payload(_):
            await view.app.page.clipboard.set(context)
            view.app.show_snack("Payload copiado para a área de transferência.")

        def send(_):
            view.app.close_modal()
            _execute_ai(provider_key)

        content = ft.Column(
            [
                ft.Text(
                    "Somente totais agregados serão enviados. Não há descrições de lançamentos, "
                    "nomes de pessoas nem dados de extratos.",
                    size=12,
                    color=theme_colors().text_muted,
                ),
                preview_field,
                ft.Row(
                    [
                        ft.TextButton("Cancelar", on_click=lambda _: view.app.close_modal()),
                        ft.OutlinedButton(
                            "Copiar payload",
                            icon=ft.Icons.CONTENT_COPY,
                            on_click=copy_payload,
                        ),
                        ft.ElevatedButton(
                            "Enviar análise",
                            icon=ft.Icons.SEND,
                            on_click=send,
                            style=primary_button_style(
                                bgcolor=meta.get("button_color", theme_colors().accent)
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
            ],
            spacing=10,
            tight=True,
        )
        view.app.show_modal(content, title=f"Preview: {provider_name}")

    def run_ai(provider_key: str):
        meta = PROVIDERS.get(provider_key, {})
        provider_name = meta.get("name", provider_key)

        if not external_calls_allowed(view.app.settings):
            view.app.show_snack(BLOCKED_MESSAGE, success=False)
            view.ai_output.value = BLOCKED_MESSAGE
            view.app.page.update()
            return

        if not provider_is_configured(view.app.settings, provider_key):
            signup = meta.get("signup_url", "")
            hint = f"Configure a API key de {provider_name} em Configurações → Integração com IA."
            if signup:
                hint += f" Obtenha em: {signup}"
            view.app.show_snack(hint, success=False)
            view.ai_output.value = hint
            view.app.page.update()
            return

        context = generate_ai_context(
            profile_id=view.app.get_view_profile_id(),
            consolidated=view.app.is_consolidated,
        )
        _show_payload_preview(provider_key, context)

    ai_buttons = []
    for provider_key, meta in PROVIDERS.items():
        ai_buttons.append(
            ft.ElevatedButton(
                meta["name"],
                icon=ft.Icons.AUTO_AWESOME,
                tooltip=meta.get("pricing_hint", ""),
                on_click=lambda _, pid=provider_key: run_ai(pid),
                style=primary_button_style(
                    bgcolor=meta.get("button_color", theme_colors().accent)
                ),
            )
        )

    def generate_pdf(e):
        from core.pdf_generator import generate_monthly_report
        from datetime import date

        today = date.today()
        try:
            path = generate_monthly_report(
                view.app.filter_year or today.year,
                view.app.filter_month or today.month,
                consolidated=view.app.is_consolidated,
                profile_id=view.app.get_view_profile_id(),
            )
            view.app.show_snack(f"PDF gerado com sucesso! Arquivo salvo em: {path}")
        except Exception as ex:
            view.app.show_snack(f"Erro ao gerar PDF: {str(ex)}", success=False)

    pdf_btn = ft.ElevatedButton(
        "Gerar Relatório PDF do Mês",
        icon=ft.Icons.PICTURE_AS_PDF,
        on_click=generate_pdf,
        style=danger_button_style(),
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Análises e previsões com IA",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=c.text_primary,
                        ),
                        view.loading_indicator,
                    ],
                    spacing=12,
                ),
                ft.Text(
                    "Cada botão usa a API key do respectivo provedor (Configurações → Integração com IA). "
                    "Antes de enviar, você revisa o payload agregado.",
                    size=12,
                    color=c.text_muted,
                ),
                ft.Row([*ai_buttons, pdf_btn], spacing=12, wrap=True),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(
                        [view.ai_output, action_row],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                    bgcolor=c.surface_alt,
                    border=ft.Border.all(1, c.border),
                    border_radius=12,
                    expand=True,
                ),
            ],
            spacing=12,
        ),
        padding=24,
        bgcolor=c.surface,
        border_radius=16,
        border=ft.Border.all(1, c.border),
    )
