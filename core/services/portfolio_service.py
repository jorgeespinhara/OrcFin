"""Portfolio operations — quotes refresh and summary."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from core.db.repositories.investment_holdings import (
    get_holdings,
    get_portfolio_evolution,
    get_quotes_map,
    save_snapshot,
    upsert_quote,
)
from core.engine.portfolio_metrics import (
    allocation_by_class,
    enrich_holding,
    portfolio_totals,
    quote_key_for_holding,
)
from core.integrations.funds.cvm_quota import fetch_fund_quota
from core.integrations.quotes.yfinance_provider import fetch_yfinance_price, yfinance_ticker
from core.models import InvestmentHolding
from core.network_policy import require_external_allowed
from core.services.portfolio_summary_cache import (
    get_cached as _get_cached_summary,
    invalidate_portfolio_summary_cache,
    quotes_enabled,
    set_cached as _set_cached_summary,
)

__all__ = [
    "get_portfolio_summary",
    "get_enriched_holdings",
    "refresh_quotes",
    "quotes_enabled",
    "invalidate_portfolio_summary_cache",
]


def _fetch_price_for_holding(
    holding: InvestmentHolding,
    *,
    fund_month_cache: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, Any] | None:
    if holding.asset_class == "fund":
        if not holding.cnpj:
            return None
        return fetch_fund_quota(holding.cnpj, month_cache=fund_month_cache)
    ticker = yfinance_ticker(holding.asset_class, holding.symbol)
    if not ticker:
        return None
    return fetch_yfinance_price(ticker)


def refresh_quotes(profile_id: int, settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    require_external_allowed(settings)
    holdings = get_holdings(profile_id)
    fund_month_cache: dict[str, list[dict[str, str]]] = {}
    seen_keys: set[str] = set()
    updated = 0
    failed = 0
    for holding in holdings:
        key = quote_key_for_holding(holding)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        try:
            result = _fetch_price_for_holding(holding, fund_month_cache=fund_month_cache)
        except Exception:
            result = None
        if result and result.get("price") is not None:
            upsert_quote(key, result["price"], result.get("provider", "unknown"))
            updated += 1
        else:
            failed += 1
    invalidate_portfolio_summary_cache(profile_id)
    summary = get_portfolio_summary(profile_id, settings=settings, refresh_snapshot=True)
    return {"updated": updated, "failed": failed, "total_value": float(summary["totals"]["market_value"])}


def get_enriched_holdings(profile_id: int) -> list[dict[str, Any]]:
    holdings = get_holdings(profile_id)
    if not holdings:
        return []
    quotes = get_quotes_map([quote_key_for_holding(h) for h in holdings])
    return [
        enrich_holding(holding, quotes.get(quote_key_for_holding(holding)))
        for holding in holdings
    ]


def _build_portfolio_summary(
    profile_id: int,
    *,
    settings: Mapping[str, Any] | None = None,
    refresh_snapshot: bool = False,
) -> dict[str, Any]:
    enriched = get_enriched_holdings(profile_id)
    totals = portfolio_totals(enriched)
    if refresh_snapshot and totals["market_value"] > 0:
        save_snapshot(profile_id, totals["market_value"], date.today())
    evolution = get_portfolio_evolution(profile_id)
    if not evolution and totals["market_value"] > 0:
        evolution = [{
            "date": date.today().isoformat(),
            "label": date.today().strftime("%d/%m"),
            "total_value": totals["market_value"],
        }]
    return {
        "holdings": enriched,
        "totals": totals,
        "allocation": allocation_by_class(enriched),
        "evolution": evolution,
        "quotes_enabled": quotes_enabled(settings),
    }


def get_portfolio_summary(
    profile_id: int,
    *,
    settings: Mapping[str, Any] | None = None,
    refresh_snapshot: bool = False,
) -> dict[str, Any]:
    if not refresh_snapshot:
        cached = _get_cached_summary(profile_id, settings)
        if cached is not None:
            return cached
    summary = _build_portfolio_summary(
        profile_id, settings=settings, refresh_snapshot=refresh_snapshot
    )
    _set_cached_summary(profile_id, settings, summary)
    return summary