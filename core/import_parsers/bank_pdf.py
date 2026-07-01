"""Dedicated PDF parsers for Brazilian bank invoices."""

from __future__ import annotations

from core.import_parsers.models import ParseResult
from core.import_parsers.pdf_parser import _extract_pdf_text, _parse_lines_from_text

_BANKS = {
    "santander_pdf": ("Santander", ("SANTANDER",)),
    "caixa_pdf": ("Caixa", ("CAIXA", "CEF", "CAIXA ECONOMICA")),
}


def is_bank_invoice_pdf(text: str, parser_id: str) -> bool:
    meta = _BANKS.get(parser_id)
    if not meta:
        return False
    upper = text[:4000].upper()
    return any(marker in upper for marker in meta[1])


def parse_bank_pdf(content: bytes, filename: str, parser_id: str) -> ParseResult:
    label, markers = _BANKS[parser_id]
    text = _extract_pdf_text(content)
    upper = text[:4000].upper()
    if not any(marker in upper for marker in markers):
        raise ValueError(f"PDF não reconhecido como fatura {label}")

    lines, warnings = _parse_lines_from_text(text)
    if not lines:
        raise ValueError(
            f"Nenhuma transação extraída do PDF ({label}). "
            "Tente exportar CSV ou OFX do banco."
        )
    if warnings:
        warnings.insert(0, f"PDF {label}: revise cada lançamento antes de confirmar.")

    return ParseResult(
        institution=f"{label} (PDF)",
        filename=filename,
        lines=lines,
        warnings=warnings,
        bank=label,
        parser_id=parser_id,
    )