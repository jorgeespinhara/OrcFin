"""Nubank credit card / account CSV parser."""

from datetime import datetime
from io import StringIO

import pandas as pd

from core.import_parsers.generic_csv import _parse_amount
from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.models import TransactionType


_DATE_COLS = {"date", "data"}
_DESC_COLS = {"title", "transaction", "descrição", "descricao", "description"}
_AMOUNT_COLS = {"amount", "valor", "value"}


def _normalize_col(name: str) -> str:
    return name.strip().lower().replace("ã", "a").replace("ç", "c")


def parse_nubank_csv(content: str, filename: str) -> ParseResult:
    try:
        df = pd.read_csv(StringIO(content), sep=None, engine="python")
    except Exception:
        df = pd.read_csv(StringIO(content))
    if df.empty:
        raise ValueError("Arquivo CSV vazio")

    colmap = {_normalize_col(c): c for c in df.columns}
    date_col = next((colmap[c] for c in _DATE_COLS if c in colmap), None)
    desc_col = next((colmap[c] for c in _DESC_COLS if c in colmap), None)
    amount_col = next((colmap[c] for c in _AMOUNT_COLS if c in colmap), None)

    if not all([date_col, desc_col, amount_col]):
        raise ValueError(
            f"Colunas esperadas (date/data, title/descrição, amount/valor). Encontradas: {list(df.columns)}"
        )

    lines: list[ParsedStatementLine] = []
    warnings: list[str] = []

    for idx, row in df.iterrows():
        try:
            raw_date = str(row[date_col]).strip()
            parsed_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                parsed_date = datetime.strptime(raw_date[:10], "%d/%m/%Y").date()
            except ValueError:
                warnings.append(f"Linha {idx + 2}: data inválida '{raw_date}'")
                continue

        description = str(row[desc_col]).strip()
        if not description or description.lower() == "nan":
            continue
        try:
            signed = _parse_amount(row[amount_col])
        except ValueError as exc:
            warnings.append(f"Linha {idx + 2}: {exc}")
            continue
        tx_type = TransactionType.INCOME if signed > 0 else TransactionType.EXPENSE
        amount = abs(signed)

        if amount == 0:
            continue

        lines.append(
            ParsedStatementLine(
                date=parsed_date,
                description=description,
                amount=amount,
                tx_type=tx_type,
            )
        )

    return ParseResult(institution="Nubank", filename=filename, lines=lines, warnings=warnings)