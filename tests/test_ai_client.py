"""Unit tests for AI provider client."""

from unittest.mock import MagicMock, patch

from core.ai.client import call_provider, probe_provider


def test_probe_claude_uses_native_sdk():
    with patch("core.ai.client.call_claude", return_value="OK") as mock_claude:
        result = probe_provider("claude", "key")

    mock_claude.assert_called_once()
    assert result["success"] is True
    assert result["response"] == "OK"


def test_openai_provider_sends_json_object():
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"summary":"ok","predictions":[],"cost_reduction_tips":[],"general_advice":"a"}'))]
    )
    with patch("core.ai.client.get_ai_client", return_value=client):
        call_provider("openai", "key", "contexto")

    assert client.chat.completions.create.call_args.kwargs["response_format"] == {"type": "json_object"}