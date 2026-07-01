from core.import_parsers.bank_csv import parse_bank_csv
from core.import_parsers.detect import detect_csv_institution, detect_format
from core.import_parsers.generic_csv import parse_generic_csv
from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.import_parsers.nubank import parse_nubank_csv
from core.import_parsers.ofx_parser import parse_ofx
from core.import_parsers.pdf_parser import parse_pdf
from core.import_parsers.plugins import load_user_plugins
from core.import_parsers.registry import list_parsers, parser_version

_BANK_PARSERS = frozenset({"inter", "c6", "bradesco", "itau", "santander", "caixa"})


def _tag(result: ParseResult, parser_id: str) -> ParseResult:
    if not result.parser_id:
        result.parser_id = parser_id
    return result


def parse_statement_file(
    content: bytes,
    filename: str,
    *,
    column_map: dict[str, str] | None = None,
) -> ParseResult:
    """Parse a bank statement file and return normalized lines."""
    load_user_plugins()
    fmt = detect_format(filename, content)

    if fmt == "ofx":
        return _tag(parse_ofx(content, filename), "ofx")

    if fmt == "pdf":
        return parse_pdf(content, filename)

    text = _decode_csv(content, (column_map or {}).get("encoding"))
    institution = detect_csv_institution(text, filename)

    if institution == "nubank":
        return _tag(parse_nubank_csv(text, filename), "nubank_csv")
    if institution in _BANK_PARSERS:
        return _tag(parse_bank_csv(text, filename, institution), institution)

    return _tag(parse_generic_csv(text, filename, column_map=column_map), "generic_csv")


def _decode_csv(content: bytes, encoding: str | None) -> str:
    for enc in (encoding, "utf-8-sig", "latin-1", "cp1252"):
        if not enc:
            continue
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


__all__ = [
    "ParseResult",
    "ParsedStatementLine",
    "list_parsers",
    "parser_version",
    "parse_statement_file",
]