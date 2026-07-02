"""Portfolio valuation and allocation metrics."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.integrations.funds.cvm_utils import normalize_cnpj
from core.integrations.quotes.yfinance_provider import ASSET_CLASS_LABELS
from core.models import InvestmentHolding


def quote_key_for_holding(holding: InvestmentHolding) -> str:
    if holding.asset_class == "fund":
        return f"fund:{normalize_cnpj(holding.cnpj)}"
    symbol = (holding.symbol or "").strip().upper()
    return f"{holding.asset_class}:{symbol}"


def cost_basis(holding: InvestmentHolding) -> Decimal:
    return holding.quantity * holding.avg_cost


_INTEGER_QTY_CLASSES = frozenset({"stock", "fii", "etf"})


def validate_holding_quantity(qty: Decimal, asset_class: str) -> str | None:
    """Return an error message when quantity is invalid for the asset class."""
    if qty <= 0:
        return "Quantidade deve ser maior que zero."
    if asset_class in _INTEGER_QTY_CLASSES and qty != qty.to_integral_value():
        return "Quantidade deve ser um número inteiro para este tipo."
    decimals = -qty.as_tuple().exponent if qty.as_tuple().exponent < 0 else 0
    if asset_class == "crypto" and decimals > 8:
        return "Quantidade de cripto: no máximo 8 casas decimais."
    if asset_class == "fund" and decimals > 6:
        return "Quantidade de cotas: no máximo 6 casas decimais."
    return None


def enrich_holding(
    holding: InvestmentHolding,
    quote: dict[str, Any] | None,
) -> dict[str, Any]:
    price = quote["price"] if quote else None
    market_value = (holding.quantity * price) if price else Decimal("0")
    cost = cost_basis(holding)
    pnl = market_value - cost if price else Decimal("0")
    pnl_pct = float((pnl / cost) * 100) if cost > 0 and price else 0.0
    return {
        "holding": holding,
        "quote_key": quote_key_for_holding(holding),
        "price": price,
        "market_value": market_value,
        "cost_basis": cost,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "has_quote": price is not None,
        "asset_class_label": ASSET_CLASS_LABELS.get(holding.asset_class, holding.asset_class),
    }


def allocation_by_class(enriched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, Decimal] = {}
    for item in enriched:
        label = item["asset_class_label"]
        totals[label] = totals.get(label, Decimal("0")) + item["market_value"]
    grand = sum(totals.values(), Decimal("0"))
    if grand <= 0:
        return []
    return [
        {
            "label": label,
            "value": float(amount),
            "pct": float((amount / grand) * 100) if grand > 0 else 0.0,
        }
        for label, amount in sorted(totals.items(), key=lambda x: x[1], reverse=True)
    ]


def market_value_for_profile(profile_id: int) -> Decimal:
    from core.db.repositories.investment_holdings import get_holdings, get_quote

    enriched = [
        enrich_holding(h, get_quote(quote_key_for_holding(h)))
        for h in get_holdings(profile_id)
    ]
    return portfolio_totals(enriched)["market_value"]


def portfolio_totals(enriched: list[dict[str, Any]]) -> dict[str, Decimal]:
    market = sum((i["market_value"] for i in enriched), Decimal("0"))
    cost = sum((i["cost_basis"] for i in enriched), Decimal("0"))
    quoted = sum((i["market_value"] for i in enriched if i["has_quote"]), Decimal("0"))
    return {
        "market_value": market,
        "cost_basis": cost,
        "pnl": market - cost,
        "quoted_value": quoted,
    }