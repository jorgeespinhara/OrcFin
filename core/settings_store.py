"""Load/save app settings with encrypted API keys."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from core.paths import ensure_app_dirs, get_config_path, migrate_legacy_layout
from core.secrets import (
    consume_legacy_key_migration,
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
)

migrate_legacy_layout()


def _settings_file() -> Path:
    ensure_app_dirs()
    return CONFIG_FILE


CONFIG_FILE = get_config_path()

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme_mode": "dark",
    "locale": "pt-BR",
    "country_profile": "BR",
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
    "mei_operational_profile": "on_demand",
    "mei_cnae": "",
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


def _normalize_locale_fields(settings: dict[str, Any]) -> dict[str, Any]:
    """Ensure locale / country_profile / currency stay coherent."""
    from core.i18n import COUNTRY_PRESETS, normalize_country, normalize_locale

    result = dict(settings)
    country = normalize_country(result.get("country_profile"))
    result["country_profile"] = country
    preset = COUNTRY_PRESETS[country]
    if not result.get("locale"):
        result["locale"] = preset["locale"]
    else:
        result["locale"] = normalize_locale(result.get("locale"))
    if not result.get("currency"):
        result["currency"] = preset["currency"]
    else:
        result["currency"] = str(result["currency"]).upper()
    return result


def _default_settings_copy() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_SETTINGS)


def load_settings() -> dict[str, Any]:
    path = _settings_file()
    if not path.exists():
        defaults = _default_settings_copy()
        from core.i18n import apply_from_settings

        apply_from_settings(defaults)
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("settings root must be a JSON object")
    except Exception:
        defaults = _default_settings_copy()
        from core.i18n import apply_from_settings

        apply_from_settings(defaults)
        return defaults

    merged = _normalize_locale_fields({**_default_settings_copy(), **data})
    decrypted = _decrypt_settings(merged)

    needs_encrypt = False
    if data.get("ai_api_key") and not is_encrypted(data.get("ai_api_key", "")):
        needs_encrypt = True
    raw_keys = data.get("ai_provider_keys") or {}
    if isinstance(raw_keys, dict) and any(v and not is_encrypted(v) for v in raw_keys.values()):
        needs_encrypt = True
    # Re-save after plaintext migration or fixed-salt → per-install salt key migration.
    if needs_encrypt or consume_legacy_key_migration():
        save_settings(decrypted)

    from core.i18n import apply_from_settings

    apply_from_settings(decrypted)
    return decrypted


def save_settings(settings: dict[str, Any]) -> None:
    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _normalize_locale_fields({**_default_settings_copy(), **settings})
    encrypted = _encrypt_settings(payload)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, indent=2, ensure_ascii=False)
    tmp.replace(path)
    from core.i18n import apply_from_settings

    apply_from_settings(payload)


def reset_preferences_after_data_wipe() -> dict[str, Any]:
    """Keep AI/backup/privacy/theme prefs; clear profile and filter state tied to wiped data."""
    current = load_settings()
    preserved = {
        key: current.get(key)
        for key in (
            "theme_mode",
            "locale",
            "country_profile",
            "currency",
            "ai_provider",
            "ai_api_key",
            "ai_model",
            "ai_base_url",
            "ai_provider_keys",
            "ai_provider_models",
            "backup_dir",
            "backup_on_close",
            "backup_interval_days",
            "backup_retention_count",
            "strict_offline",
            "portfolio_quotes_enabled",
            "portfolio_quote_refresh_minutes",
        )
    }
    fresh = _default_settings_copy()
    fresh.update(preserved)
    save_settings(fresh)
    return fresh


def wipe_all_settings() -> dict[str, Any]:
    """Remove settings file and restore factory defaults (clean install)."""
    path = _settings_file()
    if path.exists():
        path.unlink()
    defaults = _default_settings_copy()
    from core.i18n import apply_from_settings

    apply_from_settings(defaults)
    return defaults