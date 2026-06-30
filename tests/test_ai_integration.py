import json

from core.ai_gateway import _parse_ai_response, _extract_json_block


def test_extract_json_block():
    raw = '```json\n{"summary": "ok", "predictions": ["a"], "cost_reduction_tips": [], "general_advice": "texto"}\n```'
    data = _extract_json_block(raw.replace("```json", "").replace("```", ""))
    assert data["summary"] == "ok"


def test_parse_ai_response_structured():
    payload = json.dumps({
        "summary": "Resumo curto",
        "predictions": ["Receitas estáveis", "Despesas sob controle"],
        "cost_reduction_tips": ["Reduzir delivery"],
        "general_advice": "Conselho detalhado aqui.",
    })
    insight = _parse_ai_response(payload, "Grok", "grok-3")
    assert insight.summary == "Resumo curto"
    assert len(insight.predictions) == 2
    assert insight.cost_reduction_tips == ["Reduzir delivery"]
    assert insight.general_advice == "Conselho detalhado aqui."