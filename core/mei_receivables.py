"""MEI accounts receivable — aging and payment tracking."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.copy import EMPTY_CELL
from core.db.repositories.mei import get_mei_invoices


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def get_receivables_aging(profile_id: int, reference_date: Optional[date] = None) -> Dict[str, Any]:
    """Bucket unpaid invoices by days overdue."""
    today = reference_date or date.today()
    invoices = get_mei_invoices(profile_id)
    buckets = {
        "current": [],
        "1_30": [],
        "31_60": [],
        "61_90": [],
        "90_plus": [],
    }
    totals = {k: Decimal("0") for k in buckets}

    for inv in invoices:
        if inv.get("paid_at"):
            continue
        amount = Decimal(str(inv["amount"]))
        due = _parse_date(inv.get("due_date")) or _parse_date(inv.get("issue_date"))
        if not due:
            continue
        days_overdue = (today - due).days

        entry = {
            "id": inv["id"],
            "invoice_number": inv["invoice_number"],
            "tomador_name": inv.get("tomador_name") or EMPTY_CELL,
            "amount": amount,
            "issue_date": inv.get("issue_date"),
            "due_date": due.isoformat(),
            "days_overdue": max(days_overdue, 0),
        }

        if days_overdue <= 0:
            key = "current"
        elif days_overdue <= 30:
            key = "1_30"
        elif days_overdue <= 60:
            key = "31_60"
        elif days_overdue <= 90:
            key = "61_90"
        else:
            key = "90_plus"

        buckets[key].append(entry)
        totals[key] += amount

    outstanding = sum(totals.values())
    return {
        "buckets": buckets,
        "totals": totals,
        "outstanding_total": outstanding,
        "unpaid_count": sum(len(v) for v in buckets.values()),
        "reference_date": today.isoformat(),
    }