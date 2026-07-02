"""AI provider catalog."""

from __future__ import annotations

from typing import Any

PROVIDERS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "requires_key": True,
        "supports_json_object": True,
        "pricing_hint": "Créditos gratuitos no cadastro (platform.deepseek.com).",
        "signup_url": "https://platform.deepseek.com/api_keys",
        "button_color": "#0EA47A",
    },
    "grok": {
        "name": "Grok (xAI)",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3-mini",
        "requires_key": True,
        "supports_json_object": False,
        "pricing_hint": "Chave em console.x.ai (cortesia ou créditos conforme a conta).",
        "signup_url": "https://console.x.ai/",
        "button_color": "#111827",
    },
    "gemini": {
        "name": "Gemini (Google)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "requires_key": True,
        "supports_json_object": True,
        "pricing_hint": "Camada gratuita com API key (aistudio.google.com).",
        "signup_url": "https://aistudio.google.com/apikey",
        "button_color": "#4285F4",
    },
    "openai": {
        "name": "ChatGPT (OpenAI)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "requires_key": True,
        "supports_json_object": True,
        "pricing_hint": "API paga; gpt-4o-mini é o mais econômico.",
        "signup_url": "https://platform.openai.com/api-keys",
        "button_color": "#10A37F",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "base_url": "https://api.anthropic.com/v1/",
        "default_model": "claude-3-5-haiku-latest",
        "requires_key": True,
        "supports_json_object": False,
        "pricing_hint": "API paga; Haiku é o modelo mais barato.",
        "signup_url": "https://console.anthropic.com/settings/keys",
        "button_color": "#D97757",
    },
}

JSON_SCHEMA_PROMPT = """
Responda APENAS com um objeto JSON válido (sem markdown, sem texto extra) neste formato:
{
  "summary": "resumo executivo em 2-4 frases",
  "predictions": ["previsão 1", "previsão 2"],
  "cost_reduction_tips": ["dica 1", "dica 2"],
  "general_advice": "conselho geral detalhado em parágrafos"
}
"""