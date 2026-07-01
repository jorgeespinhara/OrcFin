"""Ticker autocomplete registry."""

from core.integrations.quotes import ticker_registry as tr


def test_search_requires_three_chars():
    assert tr.search_tickers("PE", "stock") == []
    assert tr.search_tickers("PET", "stock", settings={"strict_offline": True})


def test_search_stock_prefix_offline():
    matches = tr.search_tickers("PET", "stock", settings={"strict_offline": True})
    symbols = {m["symbol"] for m in matches}
    assert "PETR4" in symbols
    assert "HGLG11" not in symbols


def test_search_fii_prefix_offline():
    matches = tr.search_tickers("HGL", "fii", settings={"strict_offline": True})
    symbols = {m["symbol"] for m in matches}
    assert "HGLG11" in symbols
    assert "PETR4" not in symbols


def test_search_crypto():
    matches = tr.search_tickers("BTC", "crypto")
    assert matches and matches[0]["symbol"] == "BTC"


def test_search_etf():
    matches = tr.search_tickers("BOV", "etf")
    symbols = {m["symbol"] for m in matches}
    assert "BOVA11" in symbols