"""Market quotes via yfinance."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

ASSET_CLASS_LABELS = {
    "stock": "Ação",
    "fii": "FII",
    "etf": "ETF",
    "crypto": "Cripto",
    "fund": "Fundo",
    "other": "Outro",
}


def yfinance_ticker(asset_class: str, symbol: str | None) -> str | None:
    raw = (symbol or "").strip().upper()
    if not raw:
        return None
    if asset_class == "crypto":
        if "-" in raw:
            return raw
        return f"{raw}-BRL"
    if asset_class in ("stock", "fii", "etf"):
        if raw.endswith(".SA"):
            return raw
        return f"{raw}.SA"
    return raw


def fetch_yfinance_price(ticker: str) -> dict[str, Any] | None:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        info = yf.Ticker(ticker)
        hist = info.history(period="5d")
        if hist is None or hist.empty:
            return None
        price = Decimal(str(hist["Close"].iloc[-1]))
        if price <= 0:
            return None
        return {"price": price, "provider": "yfinance", "ticker": ticker}
    except Exception:
        return None