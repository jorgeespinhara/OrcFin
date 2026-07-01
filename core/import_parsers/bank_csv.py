"""Brazilian bank CSV parsers built on generic column detection."""

from core.import_parsers.generic_csv import parse_generic_csv
from core.import_parsers.models import ParseResult

_LABELS = {
    "inter": "Banco Inter",
    "c6": "C6 Bank",
    "bradesco": "Bradesco",
    "itau": "Itaú",
    "santander": "Santander",
    "caixa": "Caixa",
}


def _strip_preamble(content: str) -> str:
    lines = [ln for ln in content.splitlines() if ln.strip()]
    while lines and "data" not in lines[0].lower() and "date" not in lines[0].lower():
        lines.pop(0)
    return "\n".join(lines)


def parse_bank_csv(content: str, filename: str, institution: str) -> ParseResult:
    result = parse_generic_csv(_strip_preamble(content), filename)
    result.institution = _LABELS.get(institution, institution)
    return result