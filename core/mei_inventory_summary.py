"""MEI light inventory — stock KPIs."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.db.repositories.mei_inventory import get_products


def get_inventory_summary(profile_id: int) -> dict[str, Any]:
    products = get_products(profile_id)
    low_stock: list[dict[str, Any]] = []
    stock_value = Decimal("0")

    for product in products:
        qty = Decimal(str(product.get("stock_qty") or 0))
        cost = product.get("cost_price")
        price = product.get("unit_price")
        unit_val = Decimal(str(cost if cost is not None else price or 0))
        stock_value += qty * unit_val

        threshold = product.get("low_stock_threshold")
        if threshold is not None and qty <= Decimal(str(threshold)):
            low_stock.append(product)

    return {
        "product_count": len(products),
        "low_stock_count": len(low_stock),
        "low_stock_products": low_stock,
        "stock_value": stock_value,
        "products": products,
    }