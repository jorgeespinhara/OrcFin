"""Tests for AI gateway — cache, fallback, single entry point."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from core.ai_gateway import (
    AIInsightResult,
    build_local_fallback_insight,
    get_financial_insights,
    request_financial_insights,
    _cache_key,
    _read_cache,
    _write_cache,
)
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.db.schema import init_database
from core.models import AIInsight, Transaction, TransactionType


@pytest.fixture(autouse=True)
def _db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    cache_dir = project_tmp_path / "ai_cache"
    monkeypatch.setattr("core.ai.cache.CACHE_DIR", cache_dir)
    monkeypatch.setattr("core.ai_gateway._CACHE_DIR", cache_dir)
    init_database()
    yield


def _seed_data():
    profile = create_profile("User")
    cat = create_category("Food", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date.today(),
            description="Market",
            amount=Decimal("100"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )
    return profile


def test_local_fallback_insight():
    profile = _seed_data()
    insight = build_local_fallback_insight(profile.id, consolidated=False)
    assert insight.provider == "Análise local (offline)"
    assert insight.model == "finance-engine"
    assert "R$" in insight.summary


def test_request_uses_fallback_when_provider_fails():
    profile = _seed_data()
    context = "contexto agregado sem PII — identidade omitida"

    with patch("core.ai.gateway.call_provider", side_effect=RuntimeError("API down")):
        result = request_financial_insights(
            provider="grok",
            api_key="test-key",
            context=context,
            profile_id=profile.id,
            consolidated=False,
        )

    assert result.used_fallback is True
    assert result.from_cache is False
    assert result.insight is not None
    assert "offline" in result.insight.provider.lower()


def test_request_without_fallback_on_error():
    profile = _seed_data()
    context = "contexto agregado sem PII — identidade omitida"

    with patch("core.ai.gateway.call_provider", side_effect=RuntimeError("API down")):
        result = request_financial_insights(
            provider="grok",
            api_key="test-key",
            context=context,
            profile_id=profile.id,
            consolidated=False,
            use_fallback_on_error=False,
        )

    assert result.used_fallback is False
    assert result.insight is None
    assert "API down" in (result.error or "")


def test_no_api_key_without_fallback():
    result = request_financial_insights(
        provider="grok",
        api_key="",
        context="ctx — identidade omitida",
        profile_id=None,
        consolidated=True,
        use_fallback_on_error=False,
    )
    assert result.insight is None
    assert result.used_fallback is False
    assert result.error


def test_request_uses_cache_on_second_call():
    profile = _seed_data()
    context = "contexto cache — identidade omitida"
    fake = AIInsight(
        provider="Grok",
        model="grok-3",
        summary="Cached insight",
        predictions=["p1"],
        cost_reduction_tips=["t1"],
        general_advice="advice",
    )

    with patch("core.ai.gateway.call_provider", return_value=fake) as mock_call:
        first = request_financial_insights(
            provider="grok",
            api_key="key",
            context=context,
            profile_id=profile.id,
            consolidated=False,
        )
        second = request_financial_insights(
            provider="grok",
            api_key="key",
            context="contexto diferente mas mesmos totais",
            profile_id=profile.id,
            consolidated=False,
        )

    assert first.from_cache is False
    assert second.from_cache is True
    assert second.insight.summary == "Cached insight"
    mock_call.assert_called_once()


def test_cache_roundtrip():
    key = _cache_key("grok", "grok-3", 1, True)
    insight = AIInsight(
        provider="Grok",
        model="grok-3",
        summary="s",
        predictions=[],
        cost_reduction_tips=[],
        general_advice="a",
    )
    _write_cache(key, insight)
    loaded = _read_cache(key)
    assert loaded is not None
    assert loaded.summary == "s"


def test_get_financial_insights_builds_context():
    fake = AIInsight(
        provider="Grok",
        model="grok-3",
        summary="ok",
        predictions=[],
        cost_reduction_tips=[],
        general_advice="advice",
    )
    with patch("core.engine.reporting.generate_ai_context", return_value="ctx — identidade omitida") as mock_ctx:
        with patch(
            "core.ai.gateway.request_financial_insights",
            return_value=AIInsightResult(insight=fake),
        ) as mock_req:
            result = get_financial_insights(
                provider="grok",
                api_key="key",
                profile_id=1,
                consolidated=False,
            )
    mock_ctx.assert_called_once_with(profile_id=1, consolidated=False)
    mock_req.assert_called_once()
    assert mock_req.call_args.kwargs["context"] == "ctx — identidade omitida"
    assert result.insight.summary == "ok"


def test_no_api_key_uses_fallback():
    result = request_financial_insights(
        provider="grok",
        api_key="",
        context="ctx — identidade omitida",
        profile_id=None,
        consolidated=True,
    )
    assert isinstance(result, AIInsightResult)
    assert result.used_fallback is True
    assert result.insight is not None


def test_call_provider_skips_json_object_for_grok():
    from core.ai.client import call_provider

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"summary":"ok","predictions":[],"cost_reduction_tips":[],"general_advice":"a"}'))]
    )
    with patch("core.ai.client.get_ai_client", return_value=client):
        call_provider("grok", "key", "contexto", model="grok-3-mini")

    kwargs = client.chat.completions.create.call_args.kwargs
    assert "response_format" not in kwargs


def test_call_provider_uses_claude_sdk():
    from core.ai.client import call_provider

    with patch("core.ai.client.call_claude", return_value='{"summary":"ok","predictions":[],"cost_reduction_tips":[],"general_advice":"a"}') as mock_claude:
        with patch("core.ai.client.get_ai_client") as mock_openai:
            call_provider("claude", "key", "contexto")

    mock_claude.assert_called_once()
    mock_openai.assert_not_called()