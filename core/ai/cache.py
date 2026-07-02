"""Local AI response cache."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.models import AIInsight

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ai_cache"
CACHE_TTL_DAYS = 30


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now().timestamp() - CACHE_TTL_DAYS * 86400
    for path in CACHE_DIR.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass
    return CACHE_DIR


def cache_key(
    provider: str,
    model: str,
    profile_id: int | None,
    consolidated: bool,
) -> str:
    from core.engine.reporting import get_current_month_summary, get_year_to_date_summary

    current = get_current_month_summary(profile_id, consolidated)
    ytd = get_year_to_date_summary(profile_id, consolidated)
    period = date.today().strftime("%Y-%m")
    totals = (
        f"{float(current['total_income']):.2f}|"
        f"{float(current['total_expense']):.2f}|"
        f"{float(current['net_savings']):.2f}|"
        f"{float(ytd['net_savings']):.2f}"
    )
    raw = "|".join([provider, model, str(profile_id), str(consolidated), period, totals])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_cache(cache_key_value: str) -> AIInsight | None:
    path = ensure_cache_dir() / f"{cache_key_value}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AIInsight(**data["insight"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("AI cache read failed for %s: %s", cache_key_value[:12], exc)
        return None


def write_cache(cache_key_value: str, insight: AIInsight) -> None:
    path = ensure_cache_dir() / f"{cache_key_value}.json"
    payload: dict[str, Any] = {
        "prompt_hash": cache_key_value,
        "created_at": datetime.now().isoformat(),
        "insight": insight.model_dump(mode="json"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")