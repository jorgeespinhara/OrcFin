"""Portfolio metrics and CVM helpers."""

from decimal import Decimal

from core.db.repositories.investment_holdings import create_holding, upsert_quote
from core.db.repositories.net_worth import get_net_worth_totals
from core.db.repositories.profiles import create_profile
from core.engine.portfolio_metrics import (
    enrich_holding,
    market_value_for_profile,
    quote_key_for_holding,
    validate_holding_quantity,
)
from core.integrations.funds.cvm_utils import format_cnpj, normalize_cnpj
from core.integrations.quotes.yfinance_provider import yfinance_ticker
from core.models import InvestmentHolding
from core.services.portfolio_service import (
    get_portfolio_summary,
    invalidate_portfolio_summary_cache,
    quotes_enabled,
)


def test_normalize_cnpj():
    assert normalize_cnpj("00.017.024/0001-53") == "00017024000153"
    assert format_cnpj("00017024000153") == "00.017.024/0001-53"


def test_yfinance_ticker_mapping():
    assert yfinance_ticker("stock", "petr4") == "PETR4.SA"
    assert yfinance_ticker("fii", "HGLG11.SA") == "HGLG11.SA"
    assert yfinance_ticker("crypto", "btc") == "BTC-BRL"


def test_portfolio_valuation_and_net_worth(fresh_db):
    profile = create_profile("Investidor")
    holding = create_holding(
        InvestmentHolding(
            profile_id=profile.id,
            asset_class="stock",
            symbol="PETR4",
            name="Petrobras",
            quantity=Decimal("10"),
            avg_cost=Decimal("30"),
        )
    )
    key = quote_key_for_holding(holding)
    upsert_quote(key, Decimal("35"), "test")
    enriched = enrich_holding(holding, {"price": Decimal("35")})
    assert enriched["market_value"] == Decimal("350")
    assert enriched["pnl"] == Decimal("50")
    assert market_value_for_profile(profile.id) == Decimal("350")

    totals = get_net_worth_totals(profile.id)
    assert totals["portfolio_value"] == Decimal("350")
    assert totals["total_assets"] == Decimal("350")

    summary = get_portfolio_summary(profile.id)
    assert len(summary["holdings"]) == 1
    assert summary["allocation"][0]["label"] == "Ação"


def test_portfolio_summary_cache(fresh_db):
    invalidate_portfolio_summary_cache()
    profile = create_profile("Investidor")
    create_holding(
        InvestmentHolding(
            profile_id=profile.id,
            asset_class="stock",
            symbol="VALE3",
            name="Vale",
            quantity=Decimal("5"),
            avg_cost=Decimal("60"),
        )
    )

    first = get_portfolio_summary(profile.id)
    second = get_portfolio_summary(profile.id)
    assert first is second

    invalidate_portfolio_summary_cache(profile.id)
    third = get_portfolio_summary(profile.id)
    assert third is not first

    create_holding(
        InvestmentHolding(
            profile_id=profile.id,
            asset_class="fii",
            symbol="HGLG11",
            name="CSHG Logística",
            quantity=Decimal("1"),
            avg_cost=Decimal("150"),
        )
    )
    fourth = get_portfolio_summary(profile.id)
    assert fourth is not third
    assert len(fourth["holdings"]) == 2


def test_validate_holding_quantity():
    assert validate_holding_quantity(Decimal("10"), "stock") is None
    assert validate_holding_quantity(Decimal("10.5"), "stock") is not None
    assert validate_holding_quantity(Decimal("0.00000001"), "crypto") is None
    assert validate_holding_quantity(Decimal("1.123456789"), "crypto") is not None
    assert validate_holding_quantity(Decimal("100.12"), "fund") is None


def test_quotes_disabled_when_strict_offline():
    assert quotes_enabled({"strict_offline": True}) is False
    assert quotes_enabled({"strict_offline": False, "portfolio_quotes_enabled": True}) is True