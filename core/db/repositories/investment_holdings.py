"""Investment holdings, quote cache, and portfolio snapshots."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.connection import get_connection
from core.models import InvestmentHolding


def _row_to_holding(row) -> InvestmentHolding:
    applied = row["applied_at"]
    return InvestmentHolding(
        id=row["id"],
        profile_id=row["profile_id"],
        asset_class=row["asset_class"],
        symbol=row["symbol"],
        cnpj=row["cnpj"],
        name=row["name"],
        quantity=Decimal(str(row["quantity"])),
        avg_cost=Decimal(str(row["avg_cost"])),
        applied_at=date.fromisoformat(applied) if applied else None,
        broker=row["broker"],
        notes=row["notes"],
    )


def create_holding(holding: InvestmentHolding) -> InvestmentHolding:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO investment_holdings (
            profile_id, asset_class, symbol, cnpj, name,
            quantity, avg_cost, applied_at, broker, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            holding.profile_id,
            holding.asset_class,
            holding.symbol,
            holding.cnpj,
            holding.name.strip(),
            float(holding.quantity),
            float(holding.avg_cost),
            holding.applied_at.isoformat() if holding.applied_at else None,
            holding.broker,
            holding.notes,
        ),
    )
    holding.id = cursor.lastrowid
    conn.commit()
    conn.close()
    _touch_snapshots(holding.profile_id)
    _invalidate_portfolio_summary_cache(holding.profile_id)
    return holding


def update_holding(holding: InvestmentHolding) -> InvestmentHolding:
    if not holding.id:
        raise ValueError("holding id required")
    conn = get_connection()
    conn.execute(
        """
        UPDATE investment_holdings
        SET asset_class = ?, symbol = ?, cnpj = ?, name = ?,
            quantity = ?, avg_cost = ?, applied_at = ?, broker = ?, notes = ?
        WHERE id = ?
        """,
        (
            holding.asset_class,
            holding.symbol,
            holding.cnpj,
            holding.name.strip(),
            float(holding.quantity),
            float(holding.avg_cost),
            holding.applied_at.isoformat() if holding.applied_at else None,
            holding.broker,
            holding.notes,
            holding.id,
        ),
    )
    conn.commit()
    conn.close()
    _touch_snapshots(holding.profile_id)
    _invalidate_portfolio_summary_cache(holding.profile_id)
    return holding


def delete_holding(holding_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT profile_id FROM investment_holdings WHERE id = ?",
        (holding_id,),
    ).fetchone()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM investment_holdings WHERE id = ?", (holding_id,))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if ok and row:
        _touch_snapshots(row["profile_id"])
        _invalidate_portfolio_summary_cache(row["profile_id"])
    return ok


def _invalidate_portfolio_summary_cache(profile_id: int) -> None:
    from core.services.portfolio_summary_cache import invalidate_portfolio_summary_cache

    invalidate_portfolio_summary_cache(profile_id)


def _touch_snapshots(profile_id: int) -> None:
    from core.db.repositories.net_worth import _maybe_snapshot
    from core.engine.portfolio_metrics import market_value_for_profile

    try:
        save_snapshot(profile_id, market_value_for_profile(profile_id))
        _maybe_snapshot(profile_id)
    except Exception:
        pass


def get_holdings(profile_id: int) -> List[InvestmentHolding]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM investment_holdings WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [_row_to_holding(r) for r in rows]


def get_holding(holding_id: int) -> Optional[InvestmentHolding]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM investment_holdings WHERE id = ?",
        (holding_id,),
    ).fetchone()
    conn.close()
    return _row_to_holding(row) if row else None


def get_quote(quote_key: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT quote_key, price, provider, fetched_at FROM investment_quotes WHERE quote_key = ?",
        (quote_key,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "quote_key": row["quote_key"],
        "price": Decimal(str(row["price"])),
        "provider": row["provider"],
        "fetched_at": row["fetched_at"],
    }


def upsert_quote(quote_key: str, price: Decimal, provider: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO investment_quotes (quote_key, price, provider, fetched_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(quote_key) DO UPDATE SET
            price = excluded.price,
            provider = excluded.provider,
            fetched_at = CURRENT_TIMESTAMP
        """,
        (quote_key, float(price), provider),
    )
    conn.commit()
    conn.close()


def save_snapshot(profile_id: int, total_value: Decimal, snapshot_date: date | None = None) -> None:
    day = (snapshot_date or date.today()).isoformat()
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM investment_snapshots WHERE profile_id = ? AND snapshot_date = ?",
        (profile_id, day),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE investment_snapshots SET total_value = ? WHERE id = ?",
            (float(total_value), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO investment_snapshots (profile_id, snapshot_date, total_value) VALUES (?, ?, ?)",
            (profile_id, day, float(total_value)),
        )
    conn.commit()
    conn.close()


def get_portfolio_evolution(profile_id: int, months_back: int = 12) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT snapshot_date, total_value
        FROM investment_snapshots
        WHERE profile_id = ?
        ORDER BY snapshot_date DESC
        LIMIT ?
        """,
        (profile_id, months_back * 2),
    ).fetchall()
    conn.close()
    return [
        {
            "date": r["snapshot_date"],
            "label": str(r["snapshot_date"])[5:10].replace("-", "/"),
            "total_value": Decimal(str(r["total_value"])),
        }
        for r in reversed(rows)
    ]