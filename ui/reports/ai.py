"""AI financial analysis panel."""

from __future__ import annotations

import flet as ft

from core.ai_gateway import PROVIDERS, get_financial_insights, provider_is_configured
from core.engine.reporting import generate_ai_context
from core.i18n import t
from core.network_policy import BLOCKED_MESSAGE, external_calls_allowed
from ui.theme import active as theme_colors, on_surface_button_style, primary_button_style


def build_ai_section(view) -> ft.Container:
    c = theme_colors()
    last_provider = {"key": None}
    loading = {"on": False}

    view.ai_output = ft.Text(
        t("rep.ai_placeholder"),
        size=13,
        color=c.text_secondary,
    )
    view.loading_indicator = ft.ProgressRing(
        visible=False, width=20, height=20, color=c.accent
    )

    disclaimer_badge = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=16, color=c.accent),
                ft.Text(
                    t("rep.ai_disclaimer"),
                    size=11,
                    color=c.text_muted,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(10, 8, 10, 8),
        bgcolor=c.surface_alt,
        border=ft.Border.all(1, c.border),
        border_radius=8,
    )

    action_row = ft.Row(spacing=8, visible=False)
    provider_buttons: list[ft.ElevatedButton] = []

    def _set_loading(on: bool):
        loading["on"] = on
        view.loading_indicator.visible = on
        for btn in provider_buttons:
            btn.disabled = on
        for ctrl in action_row.controls:
            if hasattr(ctrl, "disabled"):
                ctrl.disabled = on

    def _set_actions_visible(visible: bool):
        action_row.visible = visible

    def _execute_ai(provider_key: str):
        if loading["on"]:
            return
        meta = PROVIDERS.get(provider_key, {})
        provider_name = meta.get("name", provider_key)
        last_provider["key"] = provider_key

        _set_loading(True)
        _set_actions_visible(False)
        view.ai_output.value = t("rep.ai_consulting", provider=provider_name)
        view.ai_output.color = c.text_secondary
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
                view.ai_output.value = t(
                    "rep.ai_failed", provider=provider_name, error=result.error
                )
                view.ai_output.color = c.danger
                view.app.show_snack(result.error, success=False)
                return

            insight = result.insight
            if result.error and result.used_fallback:
                view.ai_output.value = t(
                    "rep.ai_fallback",
                    provider=provider_name,
                    error=result.error,
                    summary=insight.summary,
                )
                view.ai_output.color = c.warning
                view.app.show_snack(result.error, success=False)
                _set_actions_visible(True)
                return

            parts = [
                t("rep.ai_header", provider=insight.provider, model=insight.model),
                insight.summary,
            ]
            if insight.predictions:
                parts.append(
                    t("rep.ai_predictions", items="\n• ".join(insight.predictions))
                )
            if insight.cost_reduction_tips:
                parts.append(
                    t(
                        "rep.ai_tips",
                        items="\n• ".join(insight.cost_reduction_tips),
                    )
                )
            if insight.general_advice and insight.general_advice != insight.summary:
                parts.append(f"\n\n{insight.general_advice}")
            if result.from_cache:
                parts.append(t("rep.ai_cache"))
            parts.append(t("rep.ai_footer"))
            view.ai_output.value = "".join(parts)
            view.ai_output.color = c.text_primary
            _set_actions_visible(True)
            view.app.show_snack(t("rep.ai_done", provider=provider_name))
        except Exception as ex:
            view.ai_output.value = t("rep.ai_error", provider=provider_name, error=ex)
            view.ai_output.color = c.danger
            view.app.show_snack(t("rep.ai_error_short", error=ex), success=False)
        finally:
            _set_loading(False)
            view.app.page.update()

    async def copy_output(_):
        text = view.ai_output.value or ""
        await view.app.page.clipboard.set(text)
        view.app.show_snack(t("rep.ai_copied"))

    def regenerate(_):
        key = last_provider["key"]
        if key and not loading["on"]:
            _execute_ai(key)

    action_row.controls = [
        ft.OutlinedButton(
            t("rep.ai_copy"),
            icon=ft.Icons.CONTENT_COPY,
            on_click=copy_output,
            style=on_surface_button_style(),
        ),
        ft.OutlinedButton(
            t("rep.ai_regenerate"),
            icon=ft.Icons.REFRESH,
            on_click=regenerate,
            style=on_surface_button_style(),
        ),
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
            view.app.show_snack(t("rep.ai_payload_copied"))

        def send(_):
            view.app.close_modal()
            _execute_ai(provider_key)

        content = ft.Column(
            [
                ft.Text(
                    t("rep.ai_payload_hint"),
                    size=12,
                    color=theme_colors().text_muted,
                ),
                preview_field,
                ft.Row(
                    [
                        ft.TextButton(
                            t("common.cancel"), on_click=lambda _: view.app.close_modal()
                        ),
                        ft.OutlinedButton(
                            t("rep.ai_copy_payload"),
                            icon=ft.Icons.CONTENT_COPY,
                            on_click=copy_payload,
                        ),
                        ft.ElevatedButton(
                            t("rep.ai_send"),
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
        view.app.show_modal(content, title=t("rep.ai_preview_title", provider=provider_name))

    def run_ai(provider_key: str):
        if loading["on"]:
            return
        meta = PROVIDERS.get(provider_key, {})
        provider_name = meta.get("name", provider_key)

        if not external_calls_allowed(view.app.settings):
            view.app.show_snack(BLOCKED_MESSAGE, success=False)
            view.ai_output.value = BLOCKED_MESSAGE
            view.ai_output.color = c.danger
            view.app.page.update()
            return

        if not provider_is_configured(view.app.settings, provider_key):
            signup = meta.get("signup_url", "")
            hint = t("rep.ai_need_key", provider=provider_name)
            if signup:
                hint += t("rep.ai_signup", url=signup)
            view.app.show_snack(hint, success=False)
            view.ai_output.value = hint
            view.ai_output.color = c.warning
            view.app.page.update()
            return

        context = generate_ai_context(
            profile_id=view.app.get_view_profile_id(),
            consolidated=view.app.is_consolidated,
        )
        _show_payload_preview(provider_key, context)

    for provider_key, meta in PROVIDERS.items():
        btn = ft.ElevatedButton(
            meta["name"],
            icon=ft.Icons.AUTO_AWESOME,
            tooltip=meta.get("pricing_hint", ""),
            on_click=lambda _, pid=provider_key: run_ai(pid),
            style=primary_button_style(
                bgcolor=meta.get("button_color", theme_colors().accent)
            ),
        )
        provider_buttons.append(btn)

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME, color=c.accent, size=22),
                        ft.Text(
                            t("rep.ai_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=c.text_primary,
                            expand=True,
                        ),
                        view.loading_indicator,
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                disclaimer_badge,
                ft.Text(
                    t("rep.ai_keys_hint"),
                    size=12,
                    color=c.text_muted,
                ),
                ft.Row(provider_buttons, spacing=12, wrap=True),
                ft.Container(height=8),
                # Fixed min height — never expand=True inside scroll parent
                # (fills the content area as a solid gray block).
                ft.Container(
                    content=ft.Column(
                        [view.ai_output, action_row],
                        spacing=12,
                        tight=True,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=20,
                    bgcolor=c.surface_alt,
                    border=ft.Border.all(1, c.border),
                    border_radius=12,
                    height=160,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        padding=24,
        bgcolor=c.surface,
        border_radius=16,
        border=ft.Border.all(1, c.border),
    )
