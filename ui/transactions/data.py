"""Transaction queries and list state."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

import flet as ft

from core.db.repositories.transactions import get_transactions, search_transactions
from core.domain.value_objects.money import format_brl
from core.models import Transaction, TransactionType
from ui.personal.period_filter import period_label

TX_LIST_LIMIT = 500
TypeFilter = Literal["all", "income", "expense"]


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


def get_type_filter(view) -> TypeFilter:
    raw = getattr(view.app, "tx_type_filter", "all") or "all"
    return raw if raw in ("all", "income", "expense") else "all"


def set_type_filter(view, value: TypeFilter) -> None:
    view.app.tx_type_filter = value


def load_transactions(view) -> list[Transaction]:
    start, end = period_bounds(view)
    query = getattr(view.app, "tx_search_query", "").strip()
    loader = search_transactions if query else get_transactions
    kwargs = dict(start_date=start, end_date=end, limit=TX_LIST_LIMIT)
    if query:
        kwargs["query"] = query
    if view.app.is_consolidated:
        txs = loader(active_profiles_only=True, **kwargs)
    else:
        profile_id = view.app.get_view_profile_id()
        if not profile_id:
            return []
        txs = loader(profile_id=profile_id, **kwargs)

    type_filter = get_type_filter(view)
    if type_filter == "income":
        txs = [t for t in txs if t.type == TransactionType.INCOME]
    elif type_filter == "expense":
        txs = [t for t in txs if t.type == TransactionType.EXPENSE]
    return txs


def period_label_for_view(view) -> str:
    return period_label(view.app.filter_year, view.app.filter_month)


def list_totals(transactions: list[Transaction]) -> dict:
    income = Decimal("0")
    expense = Decimal("0")
    for tx in transactions:
        if tx.type == TransactionType.INCOME:
            income += Decimal(str(tx.amount))
        else:
            expense += Decimal(str(tx.amount))
    return {
        "income": income,
        "expense": expense,
        "net": income - expense,
        "count": len(transactions),
        "capped": len(transactions) >= TX_LIST_LIMIT,
    }


def group_by_date(transactions: list[Transaction]) -> list[tuple[date, list[Transaction]]]:
    groups: dict[date, list[Transaction]] = {}
    for tx in transactions:
        groups.setdefault(tx.date, []).append(tx)
    # Newest first
    return sorted(groups.items(), key=lambda item: item[0], reverse=True)


def format_date_header(day: date, today: date | None = None) -> str:
    today = today or date.today()
    if day == today:
        prefix = "Hoje"
    elif day == today - timedelta(days=1):
        prefix = "Ontem"
    else:
        months = (
            "",
            "jan",
            "fev",
            "mar",
            "abr",
            "mai",
            "jun",
            "jul",
            "ago",
            "set",
            "out",
            "nov",
            "dez",
        )
        prefix = f"{day.day:02d} {months[day.month]} {day.year}"
    return prefix


def apply_search(view, e: ft.ControlEvent | None = None, *, query: str | None = None):
    if query is not None:
        view.app.tx_search_query = query.strip()
    elif e is not None:
        view.app.tx_search_query = (e.control.value or "").strip()
    view.transactions = load_transactions(view)
    view.app.refresh_current_view()


def clear_search(view, _=None):
    view.app.tx_search_query = ""
    view.transactions = load_transactions(view)
    view.app.refresh_current_view()


def apply_type_filter(view, value: TypeFilter):
    set_type_filter(view, value)
    view.transactions = load_transactions(view)
    view.app.refresh_current_view()


def recent_category_ids(view, tx_type: TransactionType, *, limit: int = 6) -> list[int]:
    """Most recently used category ids for the given type (current list snapshot)."""
    seen: list[int] = []
    for tx in view.transactions:
        if tx.type != tx_type:
            continue
        if tx.category_id in seen:
            continue
        seen.append(tx.category_id)
        if len(seen) >= limit:
            break
    return seen


def parse_brl_amount(raw: str | None) -> Decimal:
    text = (raw or "").strip().replace("R$", "").replace(" ", "")
    if not text:
        raise ValueError("empty")
    if "," in text and "." in text:
        # 1.234,56
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return Decimal(text)


def format_amount_input(amount: Decimal | float | str) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    # Keep form field simple: 1234.56 style parseable; display helper uses format_brl
    return f"{value:.2f}".replace(".", ",")
