"""Upcoming due dates — cards, recurrences, MEI DAS (local, no cloud)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.repositories.credit_cards import get_credit_cards
from core.db.repositories.mei import get_mei_config
from core.db.repositories.profiles import get_all_profiles
from core.domain.entities.mei_profile import MeiProfile
from core.engine.recurrence_detection import detect_recurring_transactions
from core.services.mei_service import das_payment_exists


def _on_day(day: int, ref: date) -> date:
    day = max(1, min(day, calendar.monthrange(ref.year, ref.month)[1]))
    if ref.day <= day:
        return ref.replace(day=day)
    y, m = (ref.year + 1, 1) if ref.month == 12 else (ref.year, ref.month + 1)
    day = min(day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def get_upcoming_due_dates(
    profile_id: Optional[int] = None,
    consolidated: bool = False,
    *,
    days_ahead: int = 45,
) -> List[Dict[str, Any]]:
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    items: List[Dict[str, Any]] = []

    profile_ids = (
        [p.id for p in get_all_profiles() if p.is_active]
        if consolidated
        else ([profile_id] if profile_id else [])
    )

    for pid in profile_ids:
        for card in get_credit_cards(pid):
            if not card.due_day:
                continue
            due = _on_day(card.due_day, today)
            if due <= cutoff:
                items.append({
                    "date": due,
                    "label": f"Fatura {card.name}",
                    "kind": "card",
                    "amount": None,
                    "profile_id": pid,
                })

        cfg = get_mei_config(pid)
        if cfg:
            entity = MeiProfile(cfg)
            das = entity.das_due_info(today)
            due = das["due_date"]
            if due <= cutoff and not das_payment_exists(pid, due.year, due.month):
                items.append({
                    "date": due,
                    "label": "DAS MEI",
                    "kind": "das",
                    "amount": entity.das_amount(),
                    "profile_id": pid,
                })

    y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    recur_due = date(y, m, 1)
    if recur_due <= cutoff:
        for rec in detect_recurring_transactions(profile_id, consolidated)[:8]:
            if rec.get("type") != "expense":
                continue
            items.append({
                "date": recur_due,
                "label": rec["description"][:40],
                "kind": "recurring",
                "amount": rec.get("average_amount"),
                "profile_id": profile_id,
            })

    items.sort(key=lambda x: x["date"])
    return items[:20]