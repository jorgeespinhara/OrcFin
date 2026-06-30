from core.import_parsers.bank_csv import parse_bank_csv
from core.import_parsers.detect import detect_csv_institution, detect_format
from core.import_parsers.generic_csv import parse_generic_csv
from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.import_parsers.nubank import parse_nubank_csv
from core.import_parsers.ofx_parser import parse_ofx
from core.import_parsers.pdf_parser import parse_pdf

_BANK_PARSERS = frozenset({"inter", "c6", "bradesco", "itau"})


def parse_statement_file(content: bytes, filename: str) -> ParseResult:
    """Parse a bank statement file and return normalized lines."""
    fmt = detect_format(filename, content)

    if fmt == "ofx":
        return parse_ofx(content, filename)

    if fmt == "pdf":
        return parse_pdf(content, filename)

    text = content.decode("utf-8-sig", errors="replace")
    institution = detect_csv_institution(text, filename)

    if institution == "nubank":
        return parse_nubank_csv(text, filename)
    if institution in _BANK_PARSERS:
        return parse_bank_csv(text, filename, institution)

    return parse_generic_csv(text, filename)


__all__ = [
    "ParseResult",
    "ParsedStatementLine",
    "parse_statement_file",
]