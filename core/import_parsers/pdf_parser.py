"""PDF statement parser (BTG, Itaú, Nubank) — pdfplumber + regex."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.models import TransactionType

# Named groups — order-independent parsing
_LINE_PATTERNS = [
    re.compile(
        r"(?P<date>\d{2}/\d{2}(?:/\d{2,4})?)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?:R\$\s*)?(?P<amount>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
    ),
    re.compile(
        r"(?P<desc>.+?)\s+"
        r"(?P<date>\d{2}/\d{2}(?:/\d{2,4})?)\s+"
        r"(?:R\$\s*)?(?P<amount>-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
    ),
]

_SKIP_KEYWORDS = (
    "saldo", "total", "pagamento", "vencimento", "limite", "resumo",
    "fatura", "período", "perido", "anterior", "subtotal",
)

_INCOME_KEYWORDS = (
    "recebido", "estorno", "credito", "crédito", "devolu", "reembolso",
)


def _detect_institution(text: str) -> str:
    upper = text[:3000].upper()
    if "BTG" in upper or "BTG PACTUAL" in upper:
        return "BTG"
    if "ITAÚ" in upper or "ITAU" in upper:
        return "Itaú"
    if "NUBANK" in upper or "NU PAGAMENTOS" in upper:
        return "Nubank"
    if "BRADESCO" in upper:
        return "Bradesco"
    if "SANTANDER" in upper:
        return "Santander"
    if "CAIXA" in upper or "CEF" in upper:
        return "Caixa"
    return "Banco (PDF)"


def _classify_pdf_tx(description: str, signed: Decimal) -> TransactionType:
    """Credit-card PDFs usually show purchases as positive amounts."""
    upper = description.upper()
    if signed < 0:
        return TransactionType.INCOME
    if any(kw in upper for kw in _INCOME_KEYWORDS):
        return TransactionType.INCOME
    return TransactionType.EXPENSE


def _parse_br_amount(raw: str) -> Decimal:
    text = raw.strip().replace("R$", "").replace(" ", "")
    negative = text.startswith("-") or text.endswith("-")
    text = text.strip("-")
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    value = Decimal(text)
    return -value if negative else value


def _parse_br_date(raw: str, default_year: int | None = None) -> date:
    parts = raw.strip().split("/")
    if len(parts) == 2:
        d, m = int(parts[0]), int(parts[1])
        y = default_year or date.today().year
    elif len(parts) == 3:
        d, m = int(parts[0]), int(parts[1])
        y = int(parts[2])
        if y < 100:
            y += 2000
    else:
        raise ValueError(raw)
    return date(y, m, d)


def _extract_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("Instale pdfplumber: pip install pdfplumber") from exc

    chunks: list[str] = []
    with pdfplumber.open(__import__("io").BytesIO(content)) as pdf:
        for page in pdf.pages:
            table_text = ""
            for table in page.extract_tables() or []:
                for row in table:
                    if row:
                        table_text += " | ".join(str(c or "") for c in row) + "\n"
            page_text = page.extract_text() or ""
            chunks.append(table_text + "\n" + page_text)
    return "\n".join(chunks)


def _parse_match(m: re.Match, year_hint: int) -> ParsedStatementLine:
    desc = m.group("desc").strip(" |-")
    if len(desc) < 2:
        raise ValueError("descrição curta")
    parsed_date = _parse_br_date(m.group("date"), year_hint)
    signed = _parse_br_amount(m.group("amount"))
    tx_type = _classify_pdf_tx(desc, signed)
    return ParsedStatementLine(
        date=parsed_date,
        description=desc[:255],
        amount=abs(signed),
        tx_type=tx_type,
    )


def _parse_lines_from_text(text: str) -> tuple[list[ParsedStatementLine], list[str]]:
    lines: list[ParsedStatementLine] = []
    warnings: list[str] = []
    year_hint = date.today().year
    year_match = re.search(r"(20\d{2})", text)
    if year_match:
        year_hint = int(year_match.group(1))

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if len(line) < 10:
            continue
        lower = line.lower()
        if any(kw in lower for kw in _SKIP_KEYWORDS):
            continue

        matched = False
        for pattern in _LINE_PATTERNS:
            m = pattern.match(line)
            if not m:
                continue
            try:
                lines.append(_parse_match(m, year_hint))
                matched = True
                break
            except Exception as exc:
                warnings.append(f"Linha ignorada '{line[:40]}...': {exc}")
                matched = True
                break
        if not matched and re.search(r"\d{2}/\d{2}", line) and re.search(r",\d{2}", line):
            warnings.append(f"Formato não reconhecido: {line[:60]}")

    return lines, warnings


def parse_pdf(content: bytes, filename: str) -> ParseResult:
    text = _extract_pdf_text(content)
    from core.import_parsers.nubank_pdf import is_nubank_invoice_pdf, parse_nubank_pdf

    if is_nubank_invoice_pdf(text):
        return parse_nubank_pdf(content, filename)

    institution = _detect_institution(text)
    lines, warnings = _parse_lines_from_text(text)

    if not lines:
        raise ValueError(
            f"Nenhuma transação extraída do PDF ({institution}). "
            "Tente exportar CSV ou OFX do banco."
        )

    if warnings:
        warnings.insert(0, "PDF é frágil. Revise cada lançamento antes de confirmar.")

    return ParseResult(
        institution=f"{institution} (PDF)",
        filename=filename,
        lines=lines,
        warnings=warnings,
    )