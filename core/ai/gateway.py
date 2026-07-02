"""Public AI gateway — cache, providers, and local fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.ai.cache import cache_key, read_cache, write_cache
from core.ai.client import call_provider, probe_provider
from core.ai.fallback import build_local_fallback_insight
from core.ai.providers import PROVIDERS
from core.models import AIInsight

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIInsightResult:
    insight: AIInsight | None
    from_cache: bool = False
    used_fallback: bool = False
    error: str | None = None


def _error_result(
    message: str,
    *,
    profile_id: int | None,
    consolidated: bool,
    use_fallback_on_error: bool,
    log: bool = True,
) -> AIInsightResult:
    if log:
        logger.warning(message)
    if use_fallback_on_error:
        return AIInsightResult(
            insight=build_local_fallback_insight(profile_id, consolidated),
            used_fallback=True,
            error=message,
        )
    return AIInsightResult(insight=None, used_fallback=False, error=message)


def request_financial_insights(
    *,
    provider: str,
    api_key: str,
    context: str,
    model: str | None = None,
    base_url: str | None = None,
    profile_id: int | None = None,
    consolidated: bool = True,
    use_fallback_on_error: bool = True,
    settings: dict[str, Any] | None = None,
) -> AIInsightResult:
    from core.audit_log import log_event
    from core.network_policy import BLOCKED_MESSAGE, external_calls_allowed
    from core.privacy import assert_no_pii_in_ai_payload

    if settings is not None and not external_calls_allowed(settings):
        log_event("ai_blocked", BLOCKED_MESSAGE, provider=provider)
        return _error_result(
            BLOCKED_MESSAGE,
            profile_id=profile_id,
            consolidated=consolidated,
            use_fallback_on_error=use_fallback_on_error,
            log=False,
        )

    if provider not in PROVIDERS:
        return _error_result(
            f"Provedor não suportado: {provider}",
            profile_id=profile_id,
            consolidated=consolidated,
            use_fallback_on_error=use_fallback_on_error,
        )

    if not api_key:
        name = PROVIDERS[provider]["name"]
        signup = PROVIDERS[provider].get("signup_url", "")
        message = (
            f"Configure a API key de {name} em Configurações → Integração com IA."
            + (f" Obtenha em: {signup}" if signup else "")
        )
        return _error_result(
            message,
            profile_id=profile_id,
            consolidated=consolidated,
            use_fallback_on_error=use_fallback_on_error,
        )

    assert_no_pii_in_ai_payload(context)

    config = PROVIDERS[provider]
    used_model = model or config.get("default_model", "default")
    resolved_base = base_url or config.get("base_url")
    key = cache_key(provider, used_model, profile_id, consolidated)

    cached = read_cache(key)
    if cached is not None:
        return AIInsightResult(insight=cached, from_cache=True)

    try:
        insight = call_provider(provider, api_key, context, model, resolved_base)
        write_cache(key, insight)
        from core.db.repositories.ai_analyses import save_analysis

        save_analysis(
            provider=provider,
            period_label=f"profile={profile_id}",
            summary=insight.summary[:400],
        )
        log_event(
            "ai_request",
            "Análise financeira enviada",
            provider=provider,
            detail=context,
        )
        return AIInsightResult(insight=insight)
    except Exception as exc:
        message = f"{config['name']}: {exc}"
        return _error_result(
            message,
            profile_id=profile_id,
            consolidated=consolidated,
            use_fallback_on_error=use_fallback_on_error,
        )


def test_connection(
    provider: str,
    api_key: str,
    base_url: str | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from core.audit_log import log_event
    from core.network_policy import BLOCKED_MESSAGE, external_calls_allowed

    if settings is not None and not external_calls_allowed(settings):
        log_event("ai_blocked", "Teste de conexão bloqueado", provider=provider)
        return {
            "success": False,
            "provider": PROVIDERS.get(provider, {}).get("name", provider),
            "error": BLOCKED_MESSAGE,
        }
    try:
        result = probe_provider(provider, api_key, base_url)
        log_event("ai_test", "Teste de conexão bem-sucedido", provider=provider)
        return result
    except Exception as exc:
        log_event("ai_test", f"Teste de conexão falhou: {exc}", provider=provider)
        return {
            "success": False,
            "provider": PROVIDERS.get(provider, {}).get("name", provider),
            "error": str(exc),
        }


def resolve_provider_api_key(settings: dict[str, Any], provider: str) -> str:
    keys = settings.get("ai_provider_keys") or {}
    if isinstance(keys, dict):
        raw = keys.get(provider)
        if raw:
            return str(raw).strip()
    if settings.get("ai_provider") == provider:
        return str(settings.get("ai_api_key") or "").strip()
    return ""


def resolve_provider_model(settings: dict[str, Any], provider: str) -> str | None:
    models = settings.get("ai_provider_models") or {}
    if isinstance(models, dict):
        raw = models.get(provider)
        if raw:
            return str(raw).strip()
    if settings.get("ai_provider") == provider:
        legacy = settings.get("ai_model")
        return str(legacy).strip() if legacy else None
    return None


def provider_is_configured(settings: dict[str, Any], provider: str) -> bool:
    return bool(resolve_provider_api_key(settings, provider))


def load_ai_config_from_settings(
    settings: dict[str, Any],
    provider: str | None = None,
) -> dict[str, Any]:
    selected = provider or settings.get("ai_provider")
    config = PROVIDERS.get(selected or "", {})
    return {
        "provider": selected,
        "api_key": resolve_provider_api_key(settings, selected or ""),
        "model": resolve_provider_model(settings, selected or ""),
        "base_url": config.get("base_url") or settings.get("ai_base_url"),
    }


def get_financial_insights(
    *,
    provider: str,
    api_key: str | None = None,
    settings: dict[str, Any] | None = None,
    profile_id: int | None = None,
    consolidated: bool = True,
    model: str | None = None,
    base_url: str | None = None,
    use_fallback_on_error: bool = False,
) -> AIInsightResult:
    from core.engine.reporting import generate_ai_context

    if settings is not None:
        api_key = resolve_provider_api_key(settings, provider)
        model = model or resolve_provider_model(settings, provider)
        base_url = base_url or PROVIDERS.get(provider, {}).get("base_url")

    context = generate_ai_context(profile_id=profile_id, consolidated=consolidated)
    return request_financial_insights(
        provider=provider,
        api_key=api_key or "",
        context=context,
        model=model,
        base_url=base_url,
        profile_id=profile_id,
        consolidated=consolidated,
        use_fallback_on_error=use_fallback_on_error,
        settings=settings,
    )