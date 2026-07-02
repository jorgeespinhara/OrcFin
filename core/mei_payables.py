"""MEI outsourcing payables — monthly consolidation by supplier."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.db.repositories.mei_orders import get_orders, get_outsource_for_order, list_unpaid_outsource


def get_monthly_payables_summary(
    profile_id: int,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    year = year or today.year
    month = month or today.month

    orders = get_orders(profile_id, year=year, month=month)
    unpaid = list_unpaid_outsource(profile_id, year, month)

    outsourced_count = 0
    in_house_count = 0
    revenue_total = Decimal("0")
    cost_total = Decimal("0")

    for order in orders:
        revenue_total += Decimal(str(order.get("revenue_amount") or 0))
        lines = get_outsource_for_order(int(order["id"]))
        if lines:
            outsourced_count += 1
            for line in lines:
                cost_total += Decimal(str(line["amount"]))
        else:
            in_house_count += 1

    by_supplier: dict[int, dict[str, Any]] = {}
    payable_total = Decimal("0")
    for row in unpaid:
        amount = Decimal(str(row["amount"]))
        payable_total += amount
        sid = int(row["supplier_id"])
        bucket = by_supplier.setdefault(
            sid,
            {
                "supplier_id": sid,
                "supplier_name": row["supplier_name"],
                "total": Decimal("0"),
                "lines": [],
            },
        )
        bucket["total"] += amount
        bucket["lines"].append(row)

    return {
        "year": year,
        "month": month,
        "order_count": len(orders),
        "in_house_count": in_house_count,
        "outsourced_count": outsourced_count,
        "revenue_total": revenue_total,
        "cost_total": cost_total,
        "margin_estimate": revenue_total - cost_total,
        "payable_total": payable_total,
        "unpaid_lines": unpaid,
        "by_supplier": list(by_supplier.values()),
    }