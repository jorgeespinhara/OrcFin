"""Net worth — assets, liabilities, and snapshots."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from core.db.connection import get_connection
from core.models import Asset, Liability


def create_asset(asset: Asset) -> Asset:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO assets (profile_id, name, asset_type, current_value, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            asset.profile_id,
            asset.name.strip(),
            asset.asset_type,
            float(asset.current_value),
            asset.notes,
        ),
    )
    asset.id = cursor.lastrowid
    conn.commit()
    conn.close()
    _maybe_snapshot(asset.profile_id)
    return asset


def create_liability(liability: Liability) -> Liability:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO liabilities (profile_id, name, liability_type, current_balance, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            liability.profile_id,
            liability.name.strip(),
            liability.liability_type,
            float(liability.current_balance),
            liability.notes,
        ),
    )
    liability.id = cursor.lastrowid
    conn.commit()
    conn.close()
    _maybe_snapshot(liability.profile_id)
    return liability


def get_assets(profile_id: int) -> List[Asset]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assets WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [
        Asset(
            id=r["id"],
            profile_id=r["profile_id"],
            name=r["name"],
            asset_type=r["asset_type"],
            current_value=Decimal(str(r["current_value"])),
            notes=r["notes"],
        )
        for r in rows
    ]


def get_liabilities(profile_id: int) -> List[Liability]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM liabilities WHERE profile_id = ? ORDER BY name",
        (profile_id,),
    ).fetchall()
    conn.close()
    return [
        Liability(
            id=r["id"],
            profile_id=r["profile_id"],
            name=r["name"],
            liability_type=r["liability_type"],
            current_balance=Decimal(str(r["current_balance"])),
            notes=r["notes"],
        )
        for r in rows
    ]


def delete_asset(asset_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT profile_id FROM assets WHERE id = ?", (asset_id,)).fetchone()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if ok and row:
        _maybe_snapshot(row["profile_id"])
    return ok


def delete_liability(liability_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT profile_id FROM liabilities WHERE id = ?", (liability_id,)).fetchone()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM liabilities WHERE id = ?", (liability_id,))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if ok and row:
        _maybe_snapshot(row["profile_id"])
    return ok


def get_net_worth_totals(profile_id: int) -> Dict[str, Decimal]:
    from core.engine.portfolio_metrics import market_value_for_profile

    assets = get_assets(profile_id)
    liabilities = get_liabilities(profile_id)
    portfolio_value = market_value_for_profile(profile_id)
    total_assets = sum((a.current_value for a in assets), Decimal("0")) + portfolio_value
    total_liabilities = sum((l.current_balance for l in liabilities), Decimal("0"))
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "portfolio_value": portfolio_value,
        "net_worth": total_assets - total_liabilities,
    }


def _maybe_snapshot(profile_id: int, *, portfolio_value: Decimal | None = None) -> None:
    if portfolio_value is None:
        totals = get_net_worth_totals(profile_id)
    else:
        assets = get_assets(profile_id)
        liabilities = get_liabilities(profile_id)
        total_assets = sum((a.current_value for a in assets), Decimal("0")) + portfolio_value
        total_liabilities = sum((l.current_balance for l in liabilities), Decimal("0"))
        totals = {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": total_assets - total_liabilities,
        }
    today = date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO net_worth_snapshots
            (profile_id, snapshot_date, total_assets, total_liabilities, net_worth)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, snapshot_date) DO UPDATE SET
                total_assets = excluded.total_assets,
                total_liabilities = excluded.total_liabilities,
                net_worth = excluded.net_worth
            """,
            (
                profile_id,
                today,
                float(totals["total_assets"]),
                float(totals["total_liabilities"]),
                float(totals["net_worth"]),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _format_snapshot_label(iso_date: str) -> str:
    try:
        return date.fromisoformat(str(iso_date)[:10]).strftime("%d/%m")
    except ValueError:
        return str(iso_date)[5:10].replace("-", "/")


def get_net_worth_evolution(profile_id: int, months_back: int = 12) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT snapshot_date, total_assets, total_liabilities, net_worth
            FROM net_worth_snapshots
            WHERE profile_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
            """,
            (profile_id, months_back * 2),
        ).fetchall()
    finally:
        conn.close()

    points = [
        {
            "date": r["snapshot_date"],
            "label": _format_snapshot_label(str(r["snapshot_date"])),
            "total_assets": Decimal(str(r["total_assets"])),
            "total_liabilities": Decimal(str(r["total_liabilities"])),
            "net_worth": Decimal(str(r["net_worth"])),
        }
        for r in reversed(rows)
    ]

    if not points:
        totals = get_net_worth_totals(profile_id)
        if totals["total_assets"] > 0 or totals["total_liabilities"] > 0:
            today = date.today().isoformat()
            points = [{
                "date": today,
                "label": date.today().strftime("%d/%m"),
                **totals,
            }]
    return points