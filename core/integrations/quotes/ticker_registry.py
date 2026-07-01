"""B3 and crypto ticker autocomplete."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from urllib.request import urlopen

from core.network_policy import external_calls_allowed
from core.paths import get_app_data_dir

BRAPI_AVAILABLE_URL = "https://brapi.dev/api/available"
_CACHE_TTL = timedelta(days=7)
_MIN_QUERY_LEN = 3

# ETFs negociados na B3 (11) — distintos de FIIs na heurística.
_KNOWN_ETFS = frozenset({
    "BOVA11", "BOVV11", "IVVB11", "SMAL11", "PIBB11", "BRAX11", "DIVO11",
    "FIND11", "MATB11", "ISUS11", "HASH11", "QBTC11", "ETHE11", "BITH11",
    "GOLD11", "XBOV11", "BOVX11", "SPXI11", "WRLD11", "EURP11", "NASD11",
    "TECB11", "XFIX11", "ESGB11", "CXAG11", "BBOV11",
})

_CRYPTO_TICKERS: list[tuple[str, str]] = [
    ("BTC", "Bitcoin"),
    ("ETH", "Ethereum"),
    ("SOL", "Solana"),
    ("ADA", "Cardano"),
    ("XRP", "Ripple"),
    ("DOGE", "Dogecoin"),
    ("DOT", "Polkadot"),
    ("AVAX", "Avalanche"),
    ("MATIC", "Polygon"),
    ("LINK", "Chainlink"),
    ("BNB", "BNB"),
    ("LTC", "Litecoin"),
    ("BCH", "Bitcoin Cash"),
    ("USDT", "Tether"),
    ("USDC", "USD Coin"),
]

_SEED_B3 = [
    "PETR4", "PETR3", "VALE3", "ITUB4", "BBDC4", "BBAS3", "WEGE3", "ABEV3",
    "B3SA3", "RENT3", "SUZB3", "ELET3", "JBSS3", "RADL3", "RAIL3", "VIVT3",
    "HGLG11", "XPLG11", "KNRI11", "MXRF11", "VISC11", "HGRU11", "BCFF11",
    "BOVA11", "IVVB11", "SMAL11", "HASH11",
]


def _cache_path() -> Path:
    path = get_app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path / "b3_tickers.json"


def _cache_fresh(path: Path) -> bool:
    if not path.is_file():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < _CACHE_TTL


def _download_b3_symbols() -> list[str]:
    with urlopen(BRAPI_AVAILABLE_URL, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    stocks = payload.get("stocks") or []
    return sorted({str(s).strip().upper() for s in stocks if s})


def _save_cache(symbols: list[str]) -> None:
    path = _cache_path()
    path.write_text(
        json.dumps({"symbols": symbols, "fetched_at": datetime.now().isoformat()}, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_cached_symbols() -> list[str]:
    path = _cache_path()
    if not path.is_file():
        return list(_SEED_B3)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        symbols = data.get("symbols") or []
        return symbols if symbols else list(_SEED_B3)
    except Exception:
        return list(_SEED_B3)


def ensure_b3_symbols(settings: Mapping[str, Any] | None = None) -> list[str]:
    """Return cached B3 symbols, refreshing from brapi when allowed."""
    path = _cache_path()
    if _cache_fresh(path):
        return _load_cached_symbols()
    if not external_calls_allowed(settings):
        return _load_cached_symbols()
    try:
        symbols = _download_b3_symbols()
        if symbols:
            _save_cache(symbols)
            return symbols
    except Exception:
        pass
    return _load_cached_symbols()


def _is_stock(symbol: str) -> bool:
    base = symbol.rstrip("F")
    return len(base) >= 5 and base[-1].isdigit() and not base.endswith("11")


def _is_fii(symbol: str) -> bool:
    return symbol.endswith("11") and symbol not in _KNOWN_ETFS


def _is_etf(symbol: str) -> bool:
    return symbol in _KNOWN_ETFS or (symbol.endswith("11") and symbol in _KNOWN_ETFS)


def _matches_class(symbol: str, asset_class: str) -> bool:
    if asset_class == "stock":
        return _is_stock(symbol)
    if asset_class == "fii":
        return _is_fii(symbol)
    if asset_class == "etf":
        return symbol in _KNOWN_ETFS or (
            symbol.endswith("11") and symbol in _KNOWN_ETFS
        )
    if asset_class in ("crypto", "other"):
        return True
    return True


def _rank_symbols(matches: list[str]) -> list[str]:
    """Prefer símbolos limpos (sem sufixo F de fracionário)."""
    def sort_key(sym: str) -> tuple:
        return (sym.endswith("F"), len(sym), sym)

    return sorted(matches, key=sort_key)


def _search_crypto(query: str, limit: int) -> list[dict[str, Any]]:
    q = query.upper()
    results: list[dict[str, Any]] = []
    for symbol, name in _CRYPTO_TICKERS:
        if symbol.startswith(q) or q in name.upper():
            results.append({"symbol": symbol, "name": name})
        if len(results) >= limit:
            break
    return results


def search_tickers(
    query: str,
    asset_class: str,
    settings: Mapping[str, Any] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Prefix search for tickers (min 3 chars)."""
    q = (query or "").strip().upper()
    if len(q) < _MIN_QUERY_LEN:
        return []

    if asset_class == "crypto":
        return _search_crypto(q, limit)

    if asset_class == "etf":
        pool = list(_KNOWN_ETFS) + [
            s for s in ensure_b3_symbols(settings) if s in _KNOWN_ETFS
        ]
        seen: set[str] = set()
        matches: list[str] = []
        for sym in sorted(set(pool)):
            if not sym.startswith(q):
                continue
            if sym in seen:
                continue
            seen.add(sym)
            matches.append(sym)
            if len(matches) >= limit:
                break
        return [{"symbol": s, "name": ""} for s in matches]

    symbols = ensure_b3_symbols(settings)
    matches = [s for s in symbols if s.startswith(q) and _matches_class(s, asset_class)]
    if asset_class == "other":
        matches = [s for s in symbols if s.startswith(q)]
    ranked = _rank_symbols(matches)[:limit]
    return [{"symbol": s, "name": ""} for s in ranked]


def lookup_ticker_name(
    symbol: str,
    asset_class: str,
    settings: Mapping[str, Any] | None = None,
) -> str:
    """Resolve display name via yfinance when online."""
    if not external_calls_allowed(settings):
        return ""
    from core.integrations.quotes.yfinance_provider import yfinance_ticker

    ticker = yfinance_ticker(asset_class, symbol)
    if not ticker:
        return ""
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
        return (
            info.get("shortName")
            or info.get("longName")
            or ""
        )
    except Exception:
        return ""