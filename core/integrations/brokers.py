"""Brazilian broker / institution names for autocomplete."""

from __future__ import annotations

BROKERS: tuple[str, ...] = (
    "XP Investimentos",
    "Rico",
    "Clear Corretora",
    "BTG Pactual",
    "Modal",
    "Nu Invest",
    "Avenue",
    "Inter",
    "Genial Investimentos",
    "Toro Investimentos",
    "Warren",
    "Órama",
    "Easynvest",
    "Banco do Brasil",
    "Itaú Corretora",
    "Bradesco Investimentos",
    "Santander",
    "Agiplan",
    "C6 Bank",
    "Mirae Asset",
    "Guide Investimentos",
    "Nova Futura",
    "Magnetis",
    "Sofisa Direto",
    "PagInvest",
    "Nubank",
    "Safra",
    "Daycoval",
    "PicPay Invest",
    "Outro",
)


def search_brokers(query: str, *, limit: int = 8) -> list[str]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    q_lower = q.lower()
    results: list[str] = []
    for name in BROKERS:
        if q_lower in name.lower():
            results.append(name)
        if len(results) >= limit:
            break
    return results