"""Transaction queries and list state."""

from __future__ import annotations

import flet as ft

from datetime import date
from calendar import monthrange
from core.db.repositories.transactions import get_transactions, search_transactions
from ui.personal.period_filter import period_label

def period_bounds(view) -> tuple[date, date]:
    year = view.app.filter_year or date.today().year
    month = view.app.filter_month
    if month:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
    else:
        start = date(year, 1, 1)
        end = date(year, 12, 31)
    return start, end

def load_transactions(view):
    start, end = period_bounds(view)
    query = getattr(view.app, "tx_search_query", "").strip()
    loader = search_transactions if query else get_transactions
    kwargs = dict(start_date=start, end_date=end, limit=500)
    if query:
        kwargs["query"] = query
    if view.app.is_consolidated:
        return loader(active_profiles_only=True, **kwargs)
    profile_id = view.app.get_view_profile_id()
    if not profile_id:
        return []
    return loader(profile_id=profile_id, **kwargs)

def period_label_for_view(view) -> str:
    return period_label(view.app.filter_year, view.app.filter_month)

def apply_search(view, e: ft.ControlEvent):
    view.app.tx_search_query = (e.control.value or "").strip()
    view.transactions = load_transactions(view)
    view.app.refresh_current_view()

def clear_search(view, _):
    view.app.tx_search_query = ""
    view.transactions = load_transactions(view)
    view.app.refresh_current_view()
