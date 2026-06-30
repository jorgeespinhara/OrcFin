"""Single official entry point for all AI — providers, cache, and local fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.domain.value_objects.money import format_brl
from core.models import AIInsight
from core.privacy import assert_no_pii_in_ai_payload

logger = logging.getLogger(__name__)

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "requires_key": True,
        "pricing_hint": "Créditos gratuitos no cadastro (platform.deepseek.com).",
        "signup_url": "https://platform.deepseek.com/api_keys",
        "button_color": "#0EA47A",
    },
    "grok": {
        "name": "Grok (xAI)",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3-mini",
        "requires_key": True,
        "pricing_hint": "Chave em console.x.ai (cortesia ou créditos conforme a conta).",
        "signup_url": "https://console.x.ai/",
        "button_color": "#111827",
    },
    "gemini": {
        "name": "Gemini (Google)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "requires_key": True,
        "pricing_hint": "Camada gratuita com API key (aistudio.google.com).",
        "signup_url": "https://aistudio.google.com/apikey",
        "button_color": "#4285F4",
    },
    "openai": {
        "name": "ChatGPT (OpenAI)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "requires_key": True,
        "pricing_hint": "API paga; gpt-4o-mini é o mais econômico.",
        "signup_url": "https://platform.openai.com/api-keys",
        "button_color": "#10A37F",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "base_url": "https://api.anthropic.com/v1/",
        "default_model": "claude-3-5-haiku-latest",
        "requires_key": True,
        "pricing_hint": "API paga; Haiku é o modelo mais barato.",
        "signup_url": "https://console.anthropic.com/settings/keys",
        "button_color": "#D97757",
    },
}

_JSON_SCHEMA_PROMPT = """
Responda APENAS com um objeto JSON válido (sem markdown, sem texto extra) neste formato:
{
  "summary": "resumo executivo em 2-4 frases",
  "predictions": ["previsão 1", "previsão 2"],
  "cost_reduction_tips": ["dica 1", "dica 2"],
  "general_advice": "conselho geral detalhado em parágrafos"
}
"""

_CACHE_DIR = Path(__file__).parent.parent / "data" / "ai_cache"


@dataclass(frozen=True, slots=True)
class AIInsightResult:
    insight: AIInsight
    from_cache: bool = False
    used_fallback: bool = False
    error: Optional[str] = None


# --- Provider internals (private) ---


def _get_ai_client(provider: str, api_key: str, base_url: Optional[str] = None):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "Pacote 'openai' não instalado. Execute: pip install -r requirements.txt"
        ) from exc

    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")

    config = PROVIDERS[provider]
    return OpenAI(api_key=api_key, base_url=base_url or config["base_url"])


def _extract_json_block(text: str) -> dict:
    # json.loads first; regex fallback when the model wraps JSON in prose
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("Resposta da IA não contém JSON válido")


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []


def _parse_ai_response(content: str, provider_name: str, model: str) -> AIInsight:
    try:
        data = _extract_json_block(content)
        summary = str(data.get("summary", "")).strip()
        predictions = _as_str_list(data.get("predictions"))
        tips = _as_str_list(data.get("cost_reduction_tips"))
        advice = str(data.get("general_advice", "")).strip()

        if not advice and summary:
            advice = summary

        return AIInsight(
            provider=provider_name,
            model=model,
            summary=summary or advice[:400],
            predictions=predictions or ["Veja análise completa abaixo."],
            cost_reduction_tips=tips,
            general_advice=advice or content,
            generated_at=datetime.now(),
        )
    except Exception:
        return AIInsight(
            provider=provider_name,
            model=model,
            summary=content[:500],
            predictions=[],
            cost_reduction_tips=[],
            general_advice=content,
            generated_at=datetime.now(),
        )


def _call_provider(
    provider: str,
    api_key: str,
    context: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AIInsight:
    client = _get_ai_client(provider, api_key, base_url)
    config = PROVIDERS[provider]
    used_model = model or config["default_model"]

    system_prompt = (
        "Você é um consultor financeiro sênior brasileiro, pragmático e direto. "
        "Responda sempre em português do Brasil. Use os dados fornecidos. "
        "Nunca invente números. Foque em recomendações práticas. "
        + _JSON_SCHEMA_PROMPT
    )

    kwargs: Dict[str, Any] = {
        "model": used_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
        "temperature": 0.4,
        "max_tokens": 2500,
    }
    try:
        response = client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        response = client.chat.completions.create(**kwargs)

    content = response.choices[0].message.content or ""
    return _parse_ai_response(content, config["name"], used_model)


def _probe_provider(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    client = _get_ai_client(provider, api_key, base_url)
    config = PROVIDERS[provider]
    model = config["default_model"]

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Responda apenas com a palavra: OK"}],
        max_tokens=5,
        temperature=0,
    )
    return {
        "success": True,
        "provider": config["name"],
        "model": model,
        "message": "Conexão bem-sucedida!",
        "response": (resp.choices[0].message.content or "").strip(),
    }


# --- Cache ---


def _ensure_cache_dir() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def _cache_key(
    provider: str,
    model: str,
    context: str,
    profile_id: Optional[int],
    consolidated: bool,
) -> str:
    raw = "|".join([
        provider,
        model,
        str(profile_id),
        str(consolidated),
        context,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_cache(cache_key: str) -> Optional[AIInsight]:
    path = _ensure_cache_dir() / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AIInsight(**data["insight"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("AI cache read failed for %s: %s", cache_key[:12], exc)
        return None


def _write_cache(cache_key: str, insight: AIInsight) -> None:
    path = _ensure_cache_dir() / f"{cache_key}.json"
    payload = {
        "prompt_hash": cache_key,
        "created_at": datetime.now().isoformat(),
        "insight": insight.model_dump(mode="json"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Public API ---


def build_local_fallback_insight(
    profile_id: Optional[int] = None,
    consolidated: bool = True,
) -> AIInsight:
    """Interpret aggregated finance data locally when the AI provider is unavailable."""
    from core.engine.reporting import get_current_month_summary, get_year_to_date_summary

    current = get_current_month_summary(profile_id, consolidated)
    ytd = get_year_to_date_summary(profile_id, consolidated)

    income = current["total_income"]
    expense = current["total_expense"]
    net = current["net_savings"]
    rate = current["savings_rate"]

    summary = (
        f"No mês atual, receitas de {format_brl(income)} e despesas de {format_brl(expense)}, "
        f"com economia líquida de {format_brl(net)} (taxa de poupança: {rate}%)."
    )

    tips: list[str] = []
    if rate < 10:
        tips.append(
            "Taxa de poupança abaixo de 10% — revise as categorias de despesa com maior volume."
        )
    if expense > income:
        tips.append(
            "Despesas superaram receitas neste período — priorize cortes em gastos não essenciais."
        )
    if ytd["savings_rate"] < rate:
        tips.append(
            "A tendência YTD está pior que o mês atual — evite novos compromissos fixos."
        )

    return AIInsight(
        provider="Análise local (offline)",
        model="finance-engine",
        summary=summary,
        predictions=[
            f"Economia acumulada no ano: {format_brl(ytd['net_savings'])} "
            f"(taxa YTD: {ytd['savings_rate']}%)."
        ],
        cost_reduction_tips=tips or [
            "Mantenha lançamentos em dia para interpretações mais precisas."
        ],
        general_advice=(
            "Esta análise foi gerada localmente pelo motor financeiro do OrcFin porque a API "
            "de IA não respondeu. Os números são calculados pelo engine — a IA apenas "
            "interpreta quando disponível."
        ),
        generated_at=datetime.now(),
    )


def request_financial_insights(
    *,
    provider: str,
    api_key: str,
    context: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    profile_id: Optional[int] = None,
    consolidated: bool = True,
    use_fallback_on_error: bool = True,
) -> AIInsightResult:
    """Request AI insights with cache and optional local fallback."""
    if provider not in PROVIDERS:
        message = f"Provedor não suportado: {provider}"
        if use_fallback_on_error:
            return AIInsightResult(
                insight=build_local_fallback_insight(profile_id, consolidated),
                used_fallback=True,
                error=message,
            )
        return AIInsightResult(
            insight=build_local_fallback_insight(profile_id, consolidated),
            used_fallback=True,
            error=message,
        )

    if not api_key:
        name = PROVIDERS[provider]["name"]
        signup = PROVIDERS[provider].get("signup_url", "")
        message = (
            f"Configure a API key de {name} em Configurações → Integração com IA."
            + (f" Obtenha em: {signup}" if signup else "")
        )
        if use_fallback_on_error:
            return AIInsightResult(
                insight=build_local_fallback_insight(profile_id, consolidated),
                used_fallback=True,
                error=message,
            )
        return AIInsightResult(
            insight=build_local_fallback_insight(profile_id, consolidated),
            used_fallback=True,
            error=message,
        )

    assert_no_pii_in_ai_payload(context)

    config = PROVIDERS[provider]
    used_model = model or config.get("default_model", "default")
    resolved_base = base_url or config.get("base_url")
    cache_key = _cache_key(provider, used_model, context, profile_id, consolidated)

    cached = _read_cache(cache_key)
    if cached is not None:
        return AIInsightResult(insight=cached, from_cache=True)

    try:
        insight = _call_provider(provider, api_key, context, model, resolved_base)
        _write_cache(cache_key, insight)
        return AIInsightResult(insight=insight)
    except Exception as exc:
        logger.warning("AI provider %s failed: %s", provider, exc)
        message = f"{config['name']}: {exc}"
        if use_fallback_on_error:
            return AIInsightResult(
                insight=build_local_fallback_insight(profile_id, consolidated),
                used_fallback=True,
                error=message,
            )
        return AIInsightResult(
            insight=build_local_fallback_insight(profile_id, consolidated),
            used_fallback=True,
            error=message,
        )


def test_connection(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Test provider connectivity — does not use cache."""
    try:
        return _probe_provider(provider, api_key, base_url)
    except Exception as exc:
        return {
            "success": False,
            "provider": PROVIDERS.get(provider, {}).get("name", provider),
            "error": str(exc),
        }


def resolve_provider_api_key(settings: Dict[str, Any], provider: str) -> str:
    """Return the API key configured for a specific provider."""
    keys = settings.get("ai_provider_keys") or {}
    if isinstance(keys, dict):
        raw = keys.get(provider)
        if raw:
            return str(raw).strip()
    if settings.get("ai_provider") == provider:
        return str(settings.get("ai_api_key") or "").strip()
    return ""


def resolve_provider_model(settings: Dict[str, Any], provider: str) -> Optional[str]:
    """Return optional model override for a provider."""
    models = settings.get("ai_provider_models") or {}
    if isinstance(models, dict):
        raw = models.get(provider)
        if raw:
            return str(raw).strip()
    if settings.get("ai_provider") == provider:
        legacy = settings.get("ai_model")
        return str(legacy).strip() if legacy else None
    return None


def provider_is_configured(settings: Dict[str, Any], provider: str) -> bool:
    return bool(resolve_provider_api_key(settings, provider))


def load_ai_config_from_settings(
    settings: Dict[str, Any],
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract AI config from app settings dict."""
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
    api_key: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    profile_id: Optional[int] = None,
    consolidated: bool = True,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
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
    )