"""Detect likely recurring transactions from historical patterns."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection


def _normalize_description(desc: str) -> str:
    text = desc.lower().strip()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text[:60]


def get_data_span_days(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> int:
    conn = get_connection()
    query = "SELECT MIN(date) AS min_d, MAX(date) AS max_d FROM transactions t"
    params: list = []
    if consolidated:
        query += " JOIN profiles p ON t.profile_id = p.id AND p.is_active = 1"
    if not consolidated and profile_id is not None:
        query += " WHERE t.profile_id = ?"
        params.append(profile_id)
    row = conn.execute(query, params).fetchone()
    conn.close()
    if not row or not row["min_d"] or not row["max_d"]:
        return 0
    start = date.fromisoformat(str(row["min_d"]))
    end = date.fromisoformat(str(row["max_d"]))
    return (end - start).days


def detect_recurring_transactions(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    min_occurrences: int = 3,
    max_deviation_pct: float = 10.0,
    lookback_months: int = 18,
) -> List[Dict[str, Any]]:
    """Find expense groups appearing in >= min_occurrences months with stable amounts."""
    conn = get_connection()
    query = """
        SELECT
            t.id,
            t.description,
            t.amount,
            t.type,
            t.category_id,
            t.date,
            c.name AS category_name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
    """
    params: list = []
    if consolidated:
        query += " JOIN profiles p ON t.profile_id = p.id AND p.is_active = 1"

    today = date.today()
    start = date(today.year, today.month, 1)
    for _ in range(lookback_months - 1):
        if start.month == 1:
            start = date(start.year - 1, 12, 1)
        else:
            start = date(start.year, start.month - 1, 1)

    query += " WHERE t.date >= ?"
    params.append(start.isoformat())

    if not consolidated and profile_id is not None:
        query += " AND t.profile_id = ?"
        params.append(profile_id)

    query += " ORDER BY t.date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        key = f"{row['type']}|{_normalize_description(row['description'])}|{row['category_id']}"
        groups[key].append(dict(row))

    results = []
    for key, txs in groups.items():
        if len(txs) < min_occurrences:
            continue

        months_seen = set()
        amounts = []
        for tx in txs:
            d = date.fromisoformat(str(tx["date"]))
            months_seen.add((d.year, d.month))
            amounts.append(float(tx["amount"]))

        if len(months_seen) < min_occurrences:
            continue

        avg_amount = mean(amounts)
        if avg_amount <= 0:
            continue
        if len(amounts) > 1:
            deviation = (pstdev(amounts) / avg_amount) * 100
        else:
            deviation = 0.0

        if deviation > max_deviation_pct:
            continue

        sample = txs[0]
        results.append({
            "description": sample["description"],
            "category_name": sample["category_name"],
            "type": sample["type"],
            "category_id": sample["category_id"],
            "average_amount": Decimal(str(round(avg_amount, 2))),
            "occurrences": len(txs),
            "distinct_months": len(months_seen),
            "amount_deviation_pct": round(deviation, 1),
            "suggested_monthly": Decimal(str(round(avg_amount, 2))),
        })

    results.sort(key=lambda x: (x["distinct_months"], float(x["average_amount"])), reverse=True)
    return results


def should_prompt_recurrence_review(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    min_days: int = 90,
) -> bool:
    span = get_data_span_days(profile_id, consolidated)
    if span < min_days:
        return False
    return len(detect_recurring_transactions(profile_id, consolidated)) > 0