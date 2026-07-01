"""Brazilian date input — DD/MM/AAAA mask and parsing."""

from __future__ import annotations

import re
from datetime import date, datetime


def format_br_date_input(raw: str) -> str:
    """Apply DD/MM/AAAA mask while typing."""
    digits = re.sub(r"\D", "", raw or "")[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def format_br_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def parse_br_date(text: str) -> date:
    """Parse DD/MM/AAAA or legacy ISO (AAAA-MM-DD)."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("invalid")