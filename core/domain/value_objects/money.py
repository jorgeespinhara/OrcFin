"""Currency formatting helpers."""

from __future__ import annotations

from decimal import Decimal


def _amount(value: Decimal | float | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _group_br_es(abs_amount: Decimal) -> str:
    """1.234,56 style (BR / ES)."""
    return f"{float(abs_amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _group_us(abs_amount: Decimal) -> str:
    """1,234.56 style (US)."""
    return f"{float(abs_amount):,.2f}"


def format_money(value: Decimal | float | int | str, currency: str | None = None) -> str:
    """Format amount for the given currency (or active app currency)."""
    amount = _amount(value)
    sign = "-" if amount < 0 else ""
    abs_amount = abs(amount)

    code = (currency or "").upper().strip()
    if not code:
        try:
            from core.i18n import get_currency

            code = get_currency() or "BRL"
        except Exception:
            code = "BRL"

    if code == "USD":
        return f"{sign}${_group_us(abs_amount)}"
    if code == "EUR":
        return f"{sign}{_group_br_es(abs_amount)} €"
    # BRL and unknown: Brazilian Real layout
    return f"{sign}R$ {_group_br_es(abs_amount)}"


def format_brl(value: Decimal | float | int | str) -> str:
    """Format using the active app currency (legacy name kept for call sites)."""
    return format_money(value)
