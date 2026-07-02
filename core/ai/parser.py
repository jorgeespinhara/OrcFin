"""Parse provider responses into AIInsight."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from core.models import AIInsight


def extract_json_block(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("Resposta da IA não contém JSON válido")


def as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []


def parse_ai_response(content: str, provider_name: str, model: str) -> AIInsight:
    try:
        data = extract_json_block(content)
        summary = str(data.get("summary", "")).strip()
        predictions = as_str_list(data.get("predictions"))
        tips = as_str_list(data.get("cost_reduction_tips"))
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