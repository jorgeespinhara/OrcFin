from core.ai_gateway import (
    PROVIDERS,
    provider_is_configured,
    resolve_provider_api_key,
    resolve_provider_model,
)
from core.settings_store import load_settings, save_settings


def test_all_report_providers_registered():
    assert set(PROVIDERS) == {"deepseek", "grok", "gemini", "openai", "claude"}


def test_resolve_provider_api_key_per_provider():
    settings = {
        "ai_provider_keys": {
            "deepseek": "sk-deep",
            "grok": "xai-key",
        },
        "ai_provider": "deepseek",
        "ai_api_key": "legacy-deep",
    }
    assert resolve_provider_api_key(settings, "deepseek") == "sk-deep"
    assert resolve_provider_api_key(settings, "grok") == "xai-key"
    assert resolve_provider_api_key(settings, "gemini") == ""
    assert provider_is_configured(settings, "deepseek") is True
    assert provider_is_configured(settings, "gemini") is False


def test_resolve_provider_model_override():
    settings = {
        "ai_provider_models": {"deepseek": "deepseek-reasoner"},
        "ai_provider": "deepseek",
        "ai_model": "deepseek-chat",
    }
    assert resolve_provider_model(settings, "deepseek") == "deepseek-reasoner"
    assert resolve_provider_model(settings, "grok") is None


def test_provider_keys_encrypted_on_save(project_tmp_path, monkeypatch):
    cfg = project_tmp_path / "config" / "settings.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("core.settings_store.CONFIG_FILE", cfg)
    save_settings(
        {
            "ai_provider_keys": {"deepseek": "sk-secret-deep"},
            "ai_provider_models": {"deepseek": "deepseek-chat"},
        }
    )
    loaded = load_settings()
    assert loaded["ai_provider_keys"]["deepseek"] == "sk-secret-deep"
    raw = cfg.read_text(encoding="utf-8")
    assert "sk-secret-deep" not in raw
    assert "enc:v1:" in raw