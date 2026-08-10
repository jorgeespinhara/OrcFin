"""Policy for optional external network usage (AI providers)."""

from __future__ import annotations

from typing import Any, Mapping


def blocked_message() -> str:
    from core.i18n import t

    return t("network.offline_blocked")


# Back-compat name: always current locale (not a frozen constant).
def __getattr__(name: str) -> Any:
    if name == "BLOCKED_MESSAGE":
        return blocked_message()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def external_calls_allowed(settings: Mapping[str, Any] | None) -> bool:
    if not settings:
        return True
    return not bool(settings.get("strict_offline"))


def require_external_allowed(settings: Mapping[str, Any] | None) -> None:
    if not external_calls_allowed(settings):
        raise PermissionError(blocked_message())