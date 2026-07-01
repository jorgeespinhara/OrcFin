"""CNPJ normalization for CVM datasets."""

from __future__ import annotations

import re


def normalize_cnpj(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def format_cnpj(digits: str) -> str:
    d = normalize_cnpj(digits)
    if len(d) != 14:
        return digits
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"