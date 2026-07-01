"""Load/save app settings with encrypted API keys."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import ensure_app_dirs, get_config_path, migrate_legacy_layout
from core.secrets import decrypt_secret, encrypt_secret, is_encrypted

migrate_legacy_layout()


def _settings_file() -> Path:
    ensure_app_dirs()
    return CONFIG_FILE


CONFIG_FILE = get_config_path()

SENSITIVE_KEYS = ("ai_api_key",)

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme_mode": "dark",
    "currency": "BRL",
    "ai_provider": None,
    "ai_api_key": None,
    "ai_model": None,
    "ai_base_url": None,
    "ai_provider_keys": {},
    "ai_provider_models": {},
    "selected_profile_id": None,
    "filter_year": None,  # resolved to current year on app load when null
    "filter_month": None,
    "projection_months_ahead": 3,
    "backup_dir": None,
    "backup_on_close": False,
    "backup_interval_days": 0,
    "backup_retention_count": 7,
    "last_backup_at": None,
    "app_mode": "personal",
    "mei_profile_id": None,
    "onboarding_completed": False,
    "setup_mode": "personal",
    "strict_offline": False,
    "portfolio_quotes_enabled": True,
    "portfolio_quote_refresh_minutes": 15,
}


def _decrypt_provider_map(values: Any) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    decrypted: dict[str, str] = {}
    for provider, raw in values.items():
        if not raw:
            continue
        if is_encrypted(raw):
            try:
                decrypted[provider] = decrypt_secret(raw)
            except Exception:
                continue
        else:
            decrypted[provider] = str(raw)
    return decrypted


def _encrypt_provider_map(values: Any) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    encrypted: dict[str, str] = {}
    for provider, raw in values.items():
        if raw:
            encrypted[provider] = encrypt_secret(str(raw))
    return encrypted


def _migrate_legacy_ai_settings(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    keys = dict(result.get("ai_provider_keys") or {})
    legacy_provider = result.get("ai_provider")
    legacy_key = result.get("ai_api_key")
    if legacy_provider and legacy_key and not keys.get(legacy_provider):
        keys[legacy_provider] = legacy_key
        result["ai_provider_keys"] = keys
    legacy_model = result.get("ai_model")
    if legacy_provider and legacy_model:
        models = dict(result.get("ai_provider_models") or {})
        if not models.get(legacy_provider):
            models[legacy_provider] = legacy_model
            result["ai_provider_models"] = models
    return result


def _decrypt_settings(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    raw_key = result.get("ai_api_key")
    if raw_key and is_encrypted(raw_key):
        try:
            result["ai_api_key"] = decrypt_secret(raw_key)
        except Exception:
            result["ai_api_key"] = None
    result["ai_provider_keys"] = _decrypt_provider_map(result.get("ai_provider_keys"))
    result = _migrate_legacy_ai_settings(result)
    return result


def _encrypt_settings(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    raw_key = result.get("ai_api_key")
    if raw_key:
        result["ai_api_key"] = encrypt_secret(raw_key)
    if result.get("ai_provider_keys"):
        result["ai_provider_keys"] = _encrypt_provider_map(result.get("ai_provider_keys"))
    return result


def load_settings() -> dict[str, Any]:
    path = _settings_file()
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_SETTINGS)

    merged = {**DEFAULT_SETTINGS, **data}
    decrypted = _decrypt_settings(merged)

    needs_encrypt = False
    if data.get("ai_api_key") and not is_encrypted(data.get("ai_api_key", "")):
        needs_encrypt = True
    raw_keys = data.get("ai_provider_keys") or {}
    if isinstance(raw_keys, dict) and any(v and not is_encrypted(v) for v in raw_keys.values()):
        needs_encrypt = True
    if needs_encrypt:
        save_settings(decrypted)

    return decrypted


def save_settings(settings: dict[str, Any]) -> None:
    path = _settings_file()
    payload = {**DEFAULT_SETTINGS, **settings}
    encrypted = _encrypt_settings(payload)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, indent=2, ensure_ascii=False)


def reset_preferences_after_data_wipe() -> dict[str, Any]:
    """Keep AI/backup/theme prefs; clear profile and filter state tied to wiped data."""
    current = load_settings()
    preserved = {
        key: current.get(key)
        for key in (
            "theme_mode",
            "currency",
            "ai_provider",
            "ai_api_key",
            "ai_model",
            "ai_base_url",
            "ai_provider_keys",
            "ai_provider_models",
            "backup_dir",
            "backup_on_close",
        )
    }
    fresh = dict(DEFAULT_SETTINGS)
    fresh.update(preserved)
    save_settings(fresh)
    return fresh


def wipe_all_settings() -> dict[str, Any]:
    """Remove settings file and restore factory defaults (clean install)."""
    path = _settings_file()
    if path.exists():
        path.unlink()
    return dict(DEFAULT_SETTINGS)