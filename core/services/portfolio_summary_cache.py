"""In-memory TTL cache for portfolio summaries — shared across views."""

from __future__ import annotations

import time
from typing import Any, Mapping

from core.network_policy import external_calls_allowed

_SUMMARY_CACHE_TTL_SECS = 90
_cache: dict[tuple[int, bool], tuple[float, dict[str, Any]]] = {}


def _quotes_flag(settings: Mapping[str, Any] | None) -> bool:
    if not external_calls_allowed(settings):
        return False
    if settings is None:
        return True
    return settings.get("portfolio_quotes_enabled", True) is not False


def _cache_key(profile_id: int, settings: Mapping[str, Any] | None) -> tuple[int, bool]:
    return profile_id, _quotes_flag(settings)


def get_cached(profile_id: int, settings: Mapping[str, Any] | None) -> dict[str, Any] | None:
    key = _cache_key(profile_id, settings)
    entry = _cache.get(key)
    if not entry:
        return None
    if time.monotonic() - entry[0] >= _SUMMARY_CACHE_TTL_SECS:
        _cache.pop(key, None)
        return None
    return entry[1]


def set_cached(profile_id: int, settings: Mapping[str, Any] | None, summary: dict[str, Any]) -> None:
    key = _cache_key(profile_id, settings)
    _cache[key] = (time.monotonic(), summary)


def invalidate_portfolio_summary_cache(profile_id: int | None = None) -> None:
    if profile_id is None:
        _cache.clear()
        return
    for key in [k for k in _cache if k[0] == profile_id]:
        _cache.pop(key, None)