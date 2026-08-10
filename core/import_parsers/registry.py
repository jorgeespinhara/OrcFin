"""Parser registry — metadata for supported import formats."""

from __future__ import annotations

from typing import Any, Callable

# Brazilian bank-specific parsers (hidden for non-BR country profiles)
_BR_ONLY_PARSERS = frozenset(
    {
        "nubank_csv",
        "nubank_pdf",
        "santander_pdf",
        "caixa_pdf",
        "inter",
        "c6",
        "bradesco",
        "itau",
        "santander",
        "caixa",
        "pdf_generic",
    }
)

PARSERS: dict[str, dict[str, Any]] = {
    "nubank_csv": {"label": "Nubank CSV", "formats": ("csv",), "version": "1"},
    "nubank_pdf": {"label": "Nubank PDF", "formats": ("pdf",), "version": "1"},
    "santander_pdf": {"label": "Santander PDF", "formats": ("pdf",), "version": "1"},
    "caixa_pdf": {"label": "Caixa PDF", "formats": ("pdf",), "version": "1"},
    "inter": {"label": "Inter", "formats": ("csv",), "version": "1"},
    "c6": {"label": "C6", "formats": ("csv",), "version": "1"},
    "bradesco": {"label": "Bradesco", "formats": ("csv",), "version": "1"},
    "itau": {"label": "Itaú", "formats": ("csv",), "version": "1"},
    "santander": {"label": "Santander", "formats": ("csv",), "version": "1"},
    "caixa": {"label": "Caixa", "formats": ("csv",), "version": "1"},
    "ofx": {"label": "OFX/QFX", "formats": ("ofx", "qfx"), "version": "1"},
    "generic_csv": {"label": "CSV genérico", "formats": ("csv",), "version": "1"},
    "pdf_generic": {"label": "PDF genérico", "formats": ("pdf",), "version": "1"},
}


def list_parsers(country: str | None = None) -> list[dict[str, Any]]:
    """List parsers; BR bank plugins only when country is BR (default)."""
    if country is None:
        try:
            from core.i18n import get_country

            country = get_country()
        except Exception:
            country = "BR"
    code = (country or "BR").upper()
    items = [{"id": k, **v} for k, v in PARSERS.items()]
    if code == "BR":
        return items
    return [p for p in items if p["id"] not in _BR_ONLY_PARSERS]


def parser_version(parser_id: str) -> str:
    return str(PARSERS.get(parser_id, {}).get("version", "1"))