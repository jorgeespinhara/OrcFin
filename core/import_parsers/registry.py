"""Parser registry — metadata for supported import formats."""

from __future__ import annotations

from typing import Any, Callable

PARSERS: dict[str, dict[str, Any]] = {
    "nubank_csv": {"label": "Nubank CSV", "formats": ("csv",), "version": "1"},
    "nubank_pdf": {"label": "Nubank PDF", "formats": ("pdf",), "version": "1"},
    "inter": {"label": "Inter", "formats": ("csv",), "version": "1"},
    "c6": {"label": "C6", "formats": ("csv",), "version": "1"},
    "bradesco": {"label": "Bradesco", "formats": ("csv",), "version": "1"},
    "itau": {"label": "Itaú", "formats": ("csv",), "version": "1"},
    "ofx": {"label": "OFX/QFX", "formats": ("ofx", "qfx"), "version": "1"},
    "generic_csv": {"label": "CSV genérico", "formats": ("csv",), "version": "1"},
    "pdf_generic": {"label": "PDF genérico", "formats": ("pdf",), "version": "1"},
}


def list_parsers() -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in PARSERS.items()]


def parser_version(parser_id: str) -> str:
    return str(PARSERS.get(parser_id, {}).get("version", "1"))