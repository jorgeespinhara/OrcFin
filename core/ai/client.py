"""HTTP clients for AI providers."""

from __future__ import annotations

from typing import Any

from core.ai.parser import parse_ai_response
from core.ai.providers import PROVIDERS, json_schema_prompt
from core.i18n import t
from core.models import AIInsight

_DEFAULT_TIMEOUT_SECONDS = 45.0


def get_ai_client(provider: str, api_key: str, base_url: str | None = None):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "Package 'openai' not installed. Run: pip install -r requirements.txt"
        ) from exc

    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")

    config = PROVIDERS[provider]
    return OpenAI(
        api_key=api_key,
        base_url=base_url or config["base_url"],
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )


def call_claude(
    api_key: str,
    context: str,
    model: str,
    system_prompt: str,
    base_url: str | None = None,
) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise ImportError(
            "Package 'anthropic' not installed. Run: pip install -r requirements.txt"
        ) from exc

    client_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": _DEFAULT_TIMEOUT_SECONDS}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = Anthropic(**client_kwargs)
    response = client.messages.create(
        model=model,
        max_tokens=2500,
        system=system_prompt,
        messages=[{"role": "user", "content": context}],
        temperature=0.4,
    )
    if not getattr(response, "content", None):
        return ""
    block = response.content[0]
    return getattr(block, "text", "") or ""


def call_provider(
    provider: str,
    api_key: str,
    context: str,
    model: str | None = None,
    base_url: str | None = None,
) -> AIInsight:
    config = PROVIDERS[provider]
    used_model = model or config["default_model"]

    system_prompt = t("ai.system_prompt") + " " + json_schema_prompt()

    if provider == "claude":
        content = call_claude(api_key, context, used_model, system_prompt, base_url=base_url)
        return parse_ai_response(content, config["name"], used_model)

    client = get_ai_client(provider, api_key, base_url)
    kwargs: dict[str, Any] = {
        "model": used_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
        "temperature": 0.4,
        "max_tokens": 2500,
    }
    if config.get("supports_json_object"):
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    choices = getattr(response, "choices", None) or []
    content = (choices[0].message.content or "") if choices else ""
    return parse_ai_response(content, config["name"], used_model)


def probe_provider(
    provider: str,
    api_key: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    if provider == "claude":
        content = call_claude(
            api_key,
            t("ai.probe_user"),
            PROVIDERS[provider]["default_model"],
            t("ai.probe_system"),
            base_url=base_url,
        )
        return {
            "success": True,
            "provider": PROVIDERS[provider]["name"],
            "model": PROVIDERS[provider]["default_model"],
            "message": t("ai.connection_ok"),
            "response": content.strip(),
        }

    client = get_ai_client(provider, api_key, base_url)
    config = PROVIDERS[provider]
    model = config["default_model"]

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": t("ai.probe_user")}],
        max_tokens=32,
        temperature=0,
    )
    choices = getattr(resp, "choices", None) or []
    text = (choices[0].message.content or "").strip() if choices else ""
    return {
        "success": True,
        "provider": config["name"],
        "model": model,
        "message": t("ai.connection_ok"),
        "response": text,
    }