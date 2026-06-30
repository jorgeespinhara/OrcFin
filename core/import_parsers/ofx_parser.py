"""OFX parser for Itaú, BTG and other banks."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.models import TransactionType


def _parse_ofx_date(value: str) -> date:
    # OFX dates: YYYYMMDD or YYYYMMDDHHMMSS
    clean = value.strip()[:8]
    return date(int(clean[0:4]), int(clean[4:6]), int(clean[6:8]))


def _detect_institution_from_ofx(text: str) -> str:
    upper = text.upper()
    if "ITAU" in upper or "ITAÚ" in upper:
        return "Itaú"
    if "BTG" in upper:
        return "BTG"
    if "NUBANK" in upper or "NU PAGAMENTOS" in upper:
        return "Nubank"
    if "BRADESCO" in upper:
        return "Bradesco"
    return "Banco (OFX)"


def parse_ofx(content: bytes, filename: str) -> ParseResult:
    try:
        from ofxparse import OfxParser
    except ImportError as exc:
        raise ImportError("Instale ofxparse: pip install ofxparse") from exc

    text = content.decode("utf-8", errors="ignore")
    institution = _detect_institution_from_ofx(text)
    ofx = OfxParser.parse(BytesIO(content))
    lines: list[ParsedStatementLine] = []
    warnings: list[str] = []

    accounts = []
    if ofx.account:
        accounts.append(ofx.account)
    accounts.extend(getattr(ofx, "accounts", []) or [])

    for account in accounts:
        statement = getattr(account, "statement", None)
        if not statement:
            continue
        for tx in getattr(statement, "transactions", []) or []:
            try:
                amount = Decimal(str(tx.amount))
            except Exception:
                warnings.append(f"Valor inválido ignorado: {tx.amount}")
                continue

            tx_type = TransactionType.INCOME if amount > 0 else TransactionType.EXPENSE
            desc = (tx.payee or tx.memo or tx.type or "Transação").strip()
            tx_date = tx.date.date() if hasattr(tx.date, "date") else _parse_ofx_date(str(tx.date))

            lines.append(
                ParsedStatementLine(
                    date=tx_date,
                    description=desc,
                    amount=abs(amount),
                    tx_type=tx_type,
                )
            )

    if not lines:
        raise ValueError("Nenhuma transação encontrada no arquivo OFX")

    return ParseResult(institution=institution, filename=filename, lines=lines, warnings=warnings)