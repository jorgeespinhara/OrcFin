"""LGPD / privacy helpers — import and AI data boundaries."""

from __future__ import annotations

import re
from typing import Iterable

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