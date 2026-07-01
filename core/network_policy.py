"""Policy for optional external network usage (AI providers)."""

from __future__ import annotations

from typing import Any, Mapping

BLOCKED_MESSAGE = (
    "Modo offline estrito ativo. Desative em Configurações → Privacidade e dados "
    "para usar integrações externas."
)


def external_calls_allowed(settings: Mapping[str, Any] | None) -> bool:
    if not settings:
        return True
    return not bool(settings.get("strict_offline"))


def require_external_allowed(settings: Mapping[str, Any] | None) -> None:
    if not external_calls_allowed(settings):
        raise PermissionError(BLOCKED_MESSAGE)