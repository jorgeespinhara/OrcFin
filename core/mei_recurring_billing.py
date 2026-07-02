"""MEI recurring billing — monthly charge summary."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.db.repositories.mei_recurring import ensure_month_charges, list_charges_for_month


def get_monthly_recurring_summary(
    profile_id: int,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    year = year or today.year
    month = month or today.month

    ensure_month_charges(profile_id, year, month)
    charges = list_charges_for_month(profile_id, year, month)
    unpaid = [c for c in charges if not c.get("paid_at")]

    expected_total = Decimal("0")
    received_total = Decimal("0")
    overdue_count = 0
    for charge in charges:
        amount = Decimal(str(charge["amount"]))
        expected_total += amount
        if charge.get("paid_at"):
            received_total += amount
        elif date.fromisoformat(str(charge["due_date"])[:10]) < today:
            overdue_count += 1

    return {
        "year": year,
        "month": month,
        "charge_count": len(charges),
        "unpaid_count": len(unpaid),
        "overdue_count": overdue_count,
        "expected_total": expected_total,
        "received_total": received_total,
        "pending_total": expected_total - received_total,
        "charges": charges,
        "unpaid_charges": unpaid,
    }