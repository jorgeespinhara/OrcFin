"""Open data export — CSV/JSON portability (LGPD-friendly)."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Optional

from core.db.repositories.categories import get_all_categories
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import get_transactions

_EXPORT_DIR = Path(__file__).parent.parent / "exports"


def export_transactions_csv(
    profile_id: Optional[int] = None,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Path:
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    path = _EXPORT_DIR / f"orcfin_lancamentos_{stamp}.csv"
    txs = get_transactions(
        profile_id=profile_id,
        start_date=start_date,
        end_date=end_date,
        active_profiles_only=profile_id is None,
        limit=100_000,
    )
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "description", "amount", "type", "category_id", "profile_id", "notes"])
        for tx in txs:
            w.writerow([
                tx.date.isoformat(),
                tx.description,
                str(tx.amount),
                tx.type.value,
                tx.category_id,
                tx.profile_id,
                tx.notes or "",
            ])
    return path


def export_open_data_json(profile_id: Optional[int] = None) -> Path:
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    path = _EXPORT_DIR / f"orcfin_dados_{stamp}.json"
    txs = get_transactions(profile_id=profile_id, active_profiles_only=profile_id is None, limit=100_000)
    payload = {
        "exported_at": date.today().isoformat(),
        "profiles": [p.model_dump(mode="json") for p in get_all_profiles()],
        "categories": [c.model_dump(mode="json") for c in get_all_categories()],
        "transactions": [tx.model_dump(mode="json") for tx in txs],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_report_summary_csv(
    *,
    year: int,
    up_to_month: int | None = None,
    profile_id: Optional[int] = None,
    consolidated: bool = False,
) -> Path:
    """Export YTD totals + monthly income/expense series (aggregates only)."""
    from core.engine.reporting import (
        get_monthly_income_expense_series,
        get_year_to_date_summary,
    )

    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    path = _EXPORT_DIR / f"orcfin_relatorio_{year}_{stamp}.csv"

    ytd = get_year_to_date_summary(
        profile_id=profile_id,
        consolidated=consolidated,
        year=year,
        up_to_month=up_to_month,
    )
    end_month = up_to_month or (date.today().month if year == date.today().year else 12)
    series = get_monthly_income_expense_series(
        months_back=12,
        end_year=year,
        end_month=end_month,
        profile_id=profile_id,
        consolidated=consolidated,
    )

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["section", "label", "value"])
        w.writerow(["ytd", "year", year])
        w.writerow(["ytd", "up_to_month", end_month])
        w.writerow(["ytd", "total_income", str(ytd["total_income"])])
        w.writerow(["ytd", "total_expense", str(ytd["total_expense"])])
        w.writerow(["ytd", "net_savings", str(ytd["net_savings"])])
        w.writerow(["ytd", "savings_rate_pct", ytd["savings_rate"]])
        w.writerow(["ytd", "transaction_count", ytd.get("transaction_count", "")])
        w.writerow([])
        w.writerow(["month", "year", "month_num", "income", "expense", "net_savings"])
        for row in series:
            w.writerow(
                [
                    row.get("label", ""),
                    row.get("year", ""),
                    row.get("month", ""),
                    str(row.get("income", "")),
                    str(row.get("expense", "")),
                    str(row.get("net_savings", "")),
                ]
            )
    return path