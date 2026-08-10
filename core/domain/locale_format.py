"""Locale-aware date display helpers."""

from __future__ import annotations

from datetime import date, datetime


def format_display_date(value: date | datetime | None, locale: str | None = None) -> str:
    """Short date for UI: MM/DD/YYYY (en-US) or DD/MM/YYYY (pt-BR, es-ES)."""
    if value is None:
        return ""
    d = value.date() if isinstance(value, datetime) else value
    code = locale
    if not code:
        try:
            from core.i18n import get_locale

            code = get_locale()
        except Exception:
            code = "pt-BR"
    if str(code).lower().startswith("en"):
        return d.strftime("%m/%d/%Y")
    return d.strftime("%d/%m/%Y")


def format_display_month_day(value: date | datetime | None, locale: str | None = None) -> str:
    if value is None:
        return ""
    d = value.date() if isinstance(value, datetime) else value
    code = locale
    if not code:
        try:
            from core.i18n import get_locale

            code = get_locale()
        except Exception:
            code = "pt-BR"
    if str(code).lower().startswith("en"):
        return d.strftime("%m/%d")
    return d.strftime("%d/%m")
