"""LGPD / privacy helpers — import and AI data boundaries."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Mapping

from core.paths import get_app_data_dir, get_database_path, get_default_backup_dir

# Patterns that must never appear in payloads sent to external AI providers.
PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bimport:", re.IGNORECASE),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),  # CPF
    re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),  # CNPJ
    re.compile(r"••••\s*\d{4}"),
    re.compile(r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b"),  # card number
)


def assert_no_pii_in_ai_payload(text: str, *, extra_forbidden: Iterable[str] = ()) -> None:
    """Raise ValueError if text contains known PII markers (dev/test guard)."""
    for pattern in PII_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"PII pattern detected in AI payload: {pattern.pattern}")
    for token in extra_forbidden:
        if token and token in text:
            raise ValueError(f"Forbidden token in AI payload: {token!r}")


def anonymize_profile_label(consolidated: bool) -> str:
    if consolidated:
        return "Visão consolidada (agregada)"
    return "Perfil individual (identidade omitida)"


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def get_local_data_summary() -> dict[str, Any]:
    db = get_database_path()
    stat = db.stat() if db.is_file() else None
    return {
        "data_root": str(get_app_data_dir()),
        "database_path": str(db),
        "database_bytes": stat.st_size if stat else 0,
        "database_modified": (
            datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            if stat
            else None
        ),
        "backup_dir": str(get_default_backup_dir()),
    }


def describe_secret_storage() -> str:
    from core.secrets import uses_system_keyring

    if uses_system_keyring():
        return "Chaves de API protegidas pelo keyring do sistema"
    return (
        "Chaves de API com proteção local derivada desta máquina "
        "(keyring do sistema indisponível)"
    )


def describe_network_policy(settings: Mapping[str, Any] | None) -> str:
    from core.network_policy import external_calls_allowed

    if external_calls_allowed(settings):
        return "Chamadas externas permitidas (somente com sua ação)"
    return "Chamadas externas bloqueadas"


def describe_ai_status(settings: Mapping[str, Any] | None) -> str:
    from core.ai_gateway import PROVIDERS, provider_is_configured
    from core.network_policy import external_calls_allowed

    if settings and not external_calls_allowed(settings):
        return "IA externa desativada pelo modo offline estrito"
    configured = [
        PROVIDERS[p]["name"]
        for p in PROVIDERS
        if settings and provider_is_configured(settings, p)
    ]
    if configured:
        names = ", ".join(configured[:3])
        if len(configured) > 3:
            names += f" (+{len(configured) - 3})"
        return f"Provedores configurados: {names}. Preview obrigatório antes do envio."
    return "Nenhum provedor configurado (análises locais continuam disponíveis)"