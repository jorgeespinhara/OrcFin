"""Nubank credit card invoice PDF parser."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.import_parsers.pdf_parser import _extract_pdf_text, _parse_br_amount
from core.models import TransactionType

_MONTH_MAP = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

_TX_LINE = re.compile(
    r"^(?P<day>\d{2})\s+(?P<mon>[A-ZÁÉÍÓÚ]{3})\s+"
    r"(?:(?:[•\.]{4})\s*(?P<last4>\d{4})\s+)?"
    r"(?P<desc>.+?)\s+"
    r"(?:[−\-])?R\$\s*(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.IGNORECASE,
)

_INSTALLMENT_IN_DESC = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")
_INSTALLMENT_FOOTER = re.compile(
    r"valor da transa[cç][aã]o de R\$\s*([\d.,]+)",
    re.IGNORECASE,
)

_SKIP_DESC = (
    "saldo restante",
    "total a pagar",
    "fatura anterior",
    "pagamentos e financiamentos",
    "valor de entrada",
    "valor da parcela",
    "juros totais",
    "pagamento mínimo",
    "pagamento minimo",
)

_INCOME_DESC = (
    "pagamento em",
    "pagamento recebido",
    "estorno",
    "reembolso",
)


def _parse_nubank_date(day: int, mon_abbr: str, year_hint: int) -> date:
    mon_key = mon_abbr.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    month = _MONTH_MAP.get(mon_key[:3])
    if not month:
        raise ValueError(mon_abbr)
    return date(year_hint, month, day)


def _detect_card_network(text: str) -> str:
    upper = text.upper()
    if re.search(r"\bAMERICAN EXPRESS\b", upper) or re.search(r"\bAMEX\b", upper):
        return "American Express"
    if re.search(r"\bHIPERCARD\b", upper):
        return "Hipercard"
    if re.search(r"\bMASTERCARD\b", upper) or re.search(r"\bMASTER CARD\b", upper):
        return "Mastercard"
    if re.search(r"\bVISA\b", upper):
        return "Visa"
    if re.search(r"\bELO\b", upper):
        return "Elo"
    if "NU PAGAMENTOS" in upper or "NUBANK" in upper:
        return "Mastercard"
    return "Mastercard"


def _extract_metadata(text: str) -> dict:
    year_hint = date.today().year
    year_match = re.search(r"FATURA\s+\d{2}\s+[A-Z]{3}\s+(20\d{2})", text, re.IGNORECASE)
    if year_match:
        year_hint = int(year_match.group(1))

    due_date = None
    due_match = re.search(
        r"Data de vencimento:\s*(\d{1,2})\s+([A-Z]{3})\s+(20\d{2})",
        text,
        re.IGNORECASE,
    )
    if due_match:
        due_date = _parse_nubank_date(int(due_match.group(1)), due_match.group(2), int(due_match.group(3)))

    period_label = None
    period_match = re.search(
        r"TRANSA[CÇ][ÕO]ES DE\s+(\d{2}\s+[A-Z]{3})\s+A\s+(\d{2}\s+[A-Z]{3})",
        text,
        re.IGNORECASE,
    )
    if period_match:
        period_label = f"{period_match.group(1)} a {period_match.group(2)}"

    statement_total = None
    total_match = re.search(
        r"RESUMO DA FATURA ATUAL.*?Total a pagar\s+R\$\s*([\d.,]+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if total_match:
        statement_total = abs(_parse_br_amount(total_match.group(1)))

    last_four = None
    last4_match = re.search(r"[•\.]{4}\s*(\d{4})", text)
    if last4_match:
        last_four = last4_match.group(1)

    return {
        "year_hint": year_hint,
        "due_date": due_date,
        "period_label": period_label,
        "statement_total": statement_total,
        "card_last_four": last_four,
        "card_network": _detect_card_network(text),
        "bank": "Nubank",
    }


def _should_skip(description: str, amount: Decimal) -> bool:
    lower = description.lower().strip()
    if amount == 0:
        return True
    if any(skip in lower for skip in _SKIP_DESC):
        return True
    if re.match(r"^[a-z].*espinhara$", lower):
        return True
    return False


def _classify_tx(description: str, raw_negative: bool) -> TransactionType:
    lower = description.lower()
    if raw_negative or any(kw in lower for kw in _INCOME_DESC):
        return TransactionType.INCOME
    return TransactionType.EXPENSE


def _parse_installment_from_desc(description: str) -> tuple[int | None, int | None]:
    match = _INSTALLMENT_IN_DESC.search(description)
    if not match:
        return None, None
    current, total = int(match.group(1)), int(match.group(2))
    if 1 <= current <= total <= 48:
        return current, total
    return None, None


def parse_nubank_pdf(content: bytes, filename: str) -> ParseResult:
    text = _extract_pdf_text(content)
    meta = _extract_metadata(text)
    year_hint = meta["year_hint"]

    lines: list[ParsedStatementLine] = []
    warnings: list[str] = []
    raw_lines = text.splitlines()
    pending_installment_idx: int | None = None

    for idx, raw in enumerate(raw_lines):
        line = " ".join(raw.split())
        if len(line) < 12:
            continue

        footer_match = _INSTALLMENT_FOOTER.search(line)
        if footer_match and pending_installment_idx is not None:
            warnings.append(
                f"Financiamento detectado em '{lines[pending_installment_idx].description[:30]}' "
                f"(transação base R$ {footer_match.group(1)})"
            )
            pending_installment_idx = None
            continue

        match = _TX_LINE.match(line)
        if not match:
            continue

        try:
            tx_date = _parse_nubank_date(int(match.group("day")), match.group("mon"), year_hint)
            description = match.group("desc").strip()
            raw_amount = match.group("amount")
            is_negative = "−" in line or line.rstrip().endswith("-") or "Pagamento" in description
            signed = _parse_br_amount(raw_amount)
            if is_negative and signed > 0:
                signed = -signed
            amount = abs(signed)

            if _should_skip(description, amount):
                continue

            inst_num, inst_total = _parse_installment_from_desc(description)
            tx_type = _classify_tx(description, signed < 0)

            parsed = ParsedStatementLine(
                date=tx_date,
                description=description[:255],
                amount=amount,
                tx_type=tx_type,
                installment_number=inst_num,
                installment_total=inst_total,
                card_last_four=match.group("last4") or meta.get("card_last_four"),
            )
            lines.append(parsed)

            if "FABIO" in description.upper() or "IOF" in line.upper():
                pending_installment_idx = len(lines) - 1
            else:
                pending_installment_idx = None
        except Exception as exc:
            warnings.append(f"Linha ignorada '{line[:50]}': {exc}")

    if not lines:
        raise ValueError("Nenhuma transação extraída da fatura Nubank (PDF).")

    deduped: list[ParsedStatementLine] = []
    seen: set[tuple] = set()
    for item in lines:
        key = (item.date, item.description, item.amount, item.tx_type.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    institution = f"Nubank • {meta['card_network']}"
    if meta.get("card_last_four"):
        institution += f" •••• {meta['card_last_four']}"

    return ParseResult(
        institution=institution,
        filename=filename,
        lines=deduped,
        warnings=warnings,
        bank=meta["bank"],
        card_network=meta["card_network"],
        card_last_four=meta.get("card_last_four"),
        statement_due_date=meta.get("due_date"),
        statement_total=meta.get("statement_total"),
        period_label=meta.get("period_label"),
        source_type="credit_card_invoice",
    )


def is_nubank_invoice_pdf(text: str) -> bool:
    upper = text.upper()
    markers = (
        "NU PAGAMENTOS",
        "NUBANK",
        "FATURA",
        "TRANSAÇÕES DE",
        "TRANSACOES DE",
        "RESUMO DA FATURA",
    )
    hits = sum(1 for marker in markers if marker in upper)
    return hits >= 3