"""BRL formatting helper."""

from __future__ import annotations

from decimal import Decimal


def format_brl(value: Decimal | float) -> str:
    """Format a numeric value as Brazilian Real (R$ 1.234,56)."""
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    sign = "-" if amount < 0 else ""
    formatted = f"R$ {float(abs(amount)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{formatted}" if sign else formatted