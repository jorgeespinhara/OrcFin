"""UI locale strings and country profile helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LOCALES = ("pt-BR", "en-US", "es-ES")
SUPPORTED_COUNTRIES = ("BR", "US", "ES")

# Flag label, locale, currency, MEI module available.
# native_name stays fixed (not translated) so the country picker is readable
# before the user has chosen a language.
COUNTRY_PRESETS: dict[str, dict[str, Any]] = {
    "BR": {
        "locale": "pt-BR",
        "currency": "BRL",
        "mei": True,
        "flag": "🇧🇷",
        "native_name": "Brasil",
        "name_key": "country.br",
    },
    "US": {
        "locale": "en-US",
        "currency": "USD",
        "mei": False,
        "flag": "🇺🇸",
        "native_name": "United States",
        "name_key": "country.us",
    },
    "ES": {
        "locale": "es-ES",
        "currency": "EUR",
        "mei": False,
        "flag": "🇪🇸",
        "native_name": "España",
        "name_key": "country.es",
    },
}

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_current_locale = "pt-BR"
_current_currency = "BRL"
_current_country = "BR"


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return "pt-BR"
    raw = str(locale).replace("_", "-")
    for code in SUPPORTED_LOCALES:
        if raw.lower() == code.lower():
            return code
    base = raw.split("-")[0].lower()
    if base == "en":
        return "en-US"
    if base == "es":
        return "es-ES"
    if base == "pt":
        return "pt-BR"
    return "pt-BR"


def normalize_country(country: str | None) -> str:
    code = (country or "BR").upper()
    return code if code in SUPPORTED_COUNTRIES else "BR"


def detect_system_locale() -> str:
    """Best-effort OS UI language → one of SUPPORTED_LOCALES."""
    candidates: list[str] = []
    try:
        import ctypes

        # Windows: user UI language (0x09 en, 0x16 pt, 0x0A es)
        lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())  # type: ignore[attr-defined]
        primary = lang_id & 0x3FF
        win_map = {0x16: "pt-BR", 0x0A: "es-ES", 0x09: "en-US"}
        if primary in win_map:
            candidates.append(win_map[primary])
    except Exception:
        pass
    try:
        import locale as _locale

        pair = _locale.getlocale()
        if pair and pair[0]:
            candidates.append(str(pair[0]))
    except Exception:
        pass
    for raw in candidates:
        if not raw:
            continue
        normalized = normalize_locale(raw.replace("_", "-"))
        if normalized in SUPPORTED_LOCALES:
            return normalized
    return "pt-BR"


def detect_system_country() -> str:
    """Suggested country from OS language (starting point; user confirms on onboarding)."""
    locale = detect_system_locale()
    for code, preset in COUNTRY_PRESETS.items():
        if preset["locale"] == locale:
            return code
    return "BR"


def supports_mei(country: str | None = None) -> bool:
    code = normalize_country(country if country is not None else _current_country)
    return bool(COUNTRY_PRESETS[code]["mei"])


def apply_locale_settings(
    *,
    locale: str | None = None,
    country_profile: str | None = None,
    currency: str | None = None,
) -> None:
    """Set active locale/currency/country for the process (from settings)."""
    global _current_locale, _current_currency, _current_country
    if country_profile is not None:
        _current_country = normalize_country(country_profile)
        preset = COUNTRY_PRESETS[_current_country]
        if locale is None:
            locale = preset["locale"]
        if currency is None:
            currency = preset["currency"]
    if locale is not None:
        _current_locale = normalize_locale(locale)
    if currency is not None:
        _current_currency = str(currency).upper() or "BRL"


def apply_from_settings(settings: dict[str, Any] | None) -> None:
    settings = settings or {}
    apply_locale_settings(
        locale=settings.get("locale"),
        country_profile=settings.get("country_profile"),
        currency=settings.get("currency"),
    )


def get_locale() -> str:
    return _current_locale


def get_currency() -> str:
    return _current_currency


def get_country() -> str:
    return _current_country


def preset_for_country(country: str | None) -> dict[str, Any]:
    return dict(COUNTRY_PRESETS[normalize_country(country)])


@lru_cache(maxsize=8)
def _load_locale_file(locale: str) -> dict[str, str]:
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def clear_locale_cache() -> None:
    _load_locale_file.cache_clear()


def t(key: str, **kwargs: Any) -> str:
    """Translate key for the active locale; fall back to pt-BR then key."""
    locale = _current_locale
    catalog = _load_locale_file(locale)
    text = catalog.get(key)
    if text is None and locale != "pt-BR":
        text = _load_locale_file("pt-BR").get(key)
    if text is None:
        text = key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
