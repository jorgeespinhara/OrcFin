"""CVM fund daily quota (VL_QUOTA) from inf_diario_fi."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.request import urlopen

from core.integrations.funds.cvm_utils import normalize_cnpj

INF_DIARIO_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{yyyymm}.zip"


def _yyyymm(d: date | None = None) -> str:
    ref = d or date.today()
    return f"{ref.year}{ref.month:02d}"


def _download_month(yyyymm: str) -> bytes:
    url = INF_DIARIO_URL.format(yyyymm=yyyymm)
    with urlopen(url, timeout=90) as resp:
        return resp.read()


def _parse_inf_diario_csv(data: bytes, yyyymm: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name = f"inf_diario_fi_{yyyymm}.csv"
        if name not in zf.namelist():
            candidates = [n for n in zf.namelist() if n.endswith(".csv")]
            if not candidates:
                return []
            name = candidates[0]
        raw = zf.read(name)
    text = raw.decode("latin-1")
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))


def _latest_quota_row(rows: list[dict[str, str]], cnpj_digits: str) -> dict[str, str] | None:
    matches = [
        r for r in rows
        if normalize_cnpj(r.get("CNPJ_FUNDO_CLASSE") or r.get("CNPJ_FUNDO") or "") == cnpj_digits
    ]
    if not matches:
        return None
    matches.sort(key=lambda r: r.get("DT_COMPTC") or "", reverse=True)
    return matches[0]


def fetch_fund_quota(cnpj: str, *, ref_date: date | None = None) -> dict[str, Any] | None:
    digits = normalize_cnpj(cnpj)
    if len(digits) != 14:
        return None
    ref = ref_date or date.today()
    for offset in range(0, 3):
        month = ref.month - offset
        year = ref.year
        while month < 1:
            month += 12
            year -= 1
        yyyymm = f"{year}{month:02d}"
        try:
            data = _download_month(yyyymm)
        except Exception:
            continue
        rows = _parse_inf_diario_csv(data, yyyymm)
        row = _latest_quota_row(rows, digits)
        if not row:
            continue
        try:
            price = Decimal(str(row.get("VL_QUOTA") or "0").replace(",", "."))
        except Exception:
            continue
        if price <= 0:
            continue
        return {
            "price": price,
            "date": row.get("DT_COMPTC"),
            "provider": "cvm",
            "yyyymm": yyyymm,
        }
    return None