"""Generic CSV parser — auto-detects date, description and amount columns."""

from datetime import datetime
from decimal import Decimal
from io import StringIO
import re

import pandas as pd

_SEP_CANDIDATES = (";", ",", "\t", None)

from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.models import TransactionType

_DATE_HINTS = ("date", "data", "dt", "dia", "vencimento")
_DESC_HINTS = ("desc", "title", "histor", "lanc", "memo", "transac", "estabelec", "nome")
_AMOUNT_HINTS = ("amount", "valor", "value", "total", "preco")
_DEBIT_HINTS = ("debito", "debit", "saida")
_CREDIT_HINTS = ("credito", "credit", "entrada")


def probe_csv_columns(content: bytes, *, encoding: str = "utf-8-sig") -> tuple[list[str], str | None]:
    """Return column names and detected separator from CSV bytes."""
    text = _decode(content, encoding)
    for sep in _SEP_CANDIDATES:
        try:
            if sep:
                df = pd.read_csv(StringIO(text), sep=sep, nrows=0)
            else:
                df = pd.read_csv(StringIO(text), sep=None, engine="python", nrows=0)
        except Exception:
            continue
        cols = [str(c) for c in df.columns]
        if len(cols) >= 2:
            return cols, sep
    raise ValueError("Não foi possível ler as colunas do CSV")


def template_to_column_map(row: dict) -> dict[str, str]:
    cmap: dict[str, str] = {
        "date_col": row["date_col"],
        "desc_col": row["desc_col"],
    }
    for key in ("amount_col", "debit_col", "credit_col", "sep", "encoding", "date_fmt"):
        if row.get(key):
            cmap[key] = row[key]
    return cmap


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


def _find_col(columns: list[str], hints: tuple[str, ...]) -> str | None:
    normalized = {_norm(c): c for c in columns}
    for hint in hints:
        for key, original in normalized.items():
            if hint in key:
                return original
    return None


def _decode(content: bytes, encoding: str) -> str:
    for enc in (encoding, "utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _parse_date(raw: str, date_fmt: str | None = None):
    raw = str(raw).strip()[:10]
    if date_fmt:
        try:
            return datetime.strptime(raw, date_fmt).date()
        except ValueError as exc:
            raise ValueError(f"data inválida: {raw}") from exc
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: {raw}")


def _parse_amount(raw: str) -> Decimal:
    text = str(raw).strip()
    if not text or text.lower() in ("nan", "none", "-"):
        return Decimal("0")
    negative = text.startswith("-") or text.startswith("(")
    text = text.replace("R$", "").replace(" ", "").replace("(", "").replace(")", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    value = Decimal(text.lstrip("-"))
    return -value if negative else value


def parse_generic_csv(
    content: str,
    filename: str,
    *,
    column_map: dict[str, str] | None = None,
) -> ParseResult:
    sep = (column_map or {}).get("sep")
    try:
        if sep:
            df = pd.read_csv(StringIO(content), sep=sep)
        else:
            df = pd.read_csv(StringIO(content), sep=None, engine="python")
    except Exception:
        df = pd.read_csv(StringIO(content))

    if df.empty or len(df.columns) < 2:
        raise ValueError("CSV vazio ou sem colunas suficientes")

    cols = list(df.columns)
    cmap = column_map or {}
    date_col = cmap.get("date_col") or _find_col(cols, _DATE_HINTS)
    desc_col = cmap.get("desc_col") or _find_col(cols, _DESC_HINTS)
    amount_col = cmap.get("amount_col") or _find_col(cols, _AMOUNT_HINTS)
    debit_col = cmap.get("debit_col") or _find_col(cols, _DEBIT_HINTS)
    credit_col = cmap.get("credit_col") or _find_col(cols, _CREDIT_HINTS)

    if not date_col:
        raise ValueError(f"Coluna de data não encontrada. Colunas: {cols}")
    if not desc_col:
        desc_col = cols[1] if len(cols) > 1 else cols[0]
    if not amount_col and not (debit_col or credit_col):
        amount_col = cols[-1]

    lines: list[ParsedStatementLine] = []
    warnings: list[str] = []

    for idx, row in df.iterrows():
        try:
            parsed_date = _parse_date(row[date_col], cmap.get("date_fmt"))
        except ValueError as exc:
            warnings.append(f"Linha {idx + 2}: {exc}")
            continue

        description = str(row[desc_col]).strip()
        if not description or description.lower() == "nan":
            continue

        if amount_col:
            signed = _parse_amount(row[amount_col])
        else:
            debit = _parse_amount(row[debit_col]) if debit_col and str(row.get(debit_col, "")).strip() else Decimal("0")
            credit = _parse_amount(row[credit_col]) if credit_col and str(row.get(credit_col, "")).strip() else Decimal("0")
            signed = credit - abs(debit) if credit else debit

        if signed == 0:
            continue

        tx_type = TransactionType.INCOME if signed > 0 else TransactionType.EXPENSE
        lines.append(
            ParsedStatementLine(
                date=parsed_date,
                description=description,
                amount=abs(signed),
                tx_type=tx_type,
            )
        )

    if not lines:
        raise ValueError("Nenhum lançamento válido no CSV genérico")

    return ParseResult(
        institution="CSV Genérico",
        filename=filename,
        lines=lines,
        warnings=warnings,
        parser_id="generic_csv",
    )