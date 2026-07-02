"""HTTP clients for AI providers."""

from __future__ import annotations

from typing import Any

from core.ai.parser import parse_ai_response
from core.ai.providers import JSON_SCHEMA_PROMPT, PROVIDERS
from core.models import AIInsight


def get_ai_client(provider: str, api_key: str, base_url: str | None = None):
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


def call_claude(api_key: str, context: str, model: str, system_prompt: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise ImportError(
            "Pacote 'anthropic' não instalado. Execute: pip install -r requirements.txt"
        ) from exc

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2500,
        system=system_prompt,
        messages=[{"role": "user", "content": context}],
        temperature=0.4,
    )
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

    system_prompt = (
        "Você é um consultor financeiro sênior brasileiro, pragmático e direto. "
        "Responda sempre em português do Brasil. Use os dados fornecidos. "
        "Nunca invente números. Foque em recomendações práticas. "
        + JSON_SCHEMA_PROMPT
    )

    if provider == "claude":
        content = call_claude(api_key, context, used_model, system_prompt)
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
    content = response.choices[0].message.content or ""
    return parse_ai_response(content, config["name"], used_model)


def probe_provider(
    provider: str,
    api_key: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    if provider == "claude":
        content = call_claude(
            api_key,
            "Responda apenas com a palavra: OK",
            PROVIDERS[provider]["default_model"],
            "Responda de forma breve.",
        )
        return {
            "success": True,
            "provider": PROVIDERS[provider]["name"],
            "model": PROVIDERS[provider]["default_model"],
            "message": "Conexão bem-sucedida!",
            "response": content.strip(),
        }

    client = get_ai_client(provider, api_key, base_url)
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