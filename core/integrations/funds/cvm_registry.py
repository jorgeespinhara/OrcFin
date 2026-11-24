"""CVM fund registry — cad_fi.csv cache and lookup."""

from __future__ import annotations

import csv
import io
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from core.integrations.funds.cvm_utils import normalize_cnpj
from core.paths import get_app_data_dir

CAD_FI_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
_CACHE_TTL = timedelta(days=7)
_SEARCH_CACHE_SECS = 300
_SEARCH_CACHE_MAX = 128
_cache_lock = threading.Lock()
_search_cache: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}
_rows_cache: tuple[Path, float, list[dict[str, str]]] | None = None


def _cache_path() -> Path:
    path = get_app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path / "cad_fi.csv"


def _cache_fresh(path: Path) -> bool:
    if not path.is_file():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < _CACHE_TTL


def _download_cad_fi() -> bytes:
    with urlopen(CAD_FI_URL, timeout=60) as resp:
        return resp.read()


def _ensure_registry_file() -> Path:
    path = _cache_path()
    if _cache_fresh(path):
        return path
    data = _download_cad_fi()
    path.write_bytes(data)
    return path


def load_registry_rows() -> list[dict[str, str]]:
    global _rows_cache
    path = _ensure_registry_file()
    mtime = path.stat().st_mtime
    with _cache_lock:
        if _rows_cache is not None and _rows_cache[0] == path and _rows_cache[1] == mtime:
            return _rows_cache[2]
    text = path.read_bytes().decode("latin-1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = [dict(row) for row in reader]
    with _cache_lock:
        _rows_cache = (path, mtime, rows)
    return rows


def search_funds(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if len(q) < 2:
        return []

    cache_key = (q.lower(), limit)
    now = time.monotonic()
    with _cache_lock:
        cached = _search_cache.get(cache_key)
        if cached and now - cached[0] < _SEARCH_CACHE_SECS:
            return cached[1]

    q_lower = q.lower()
    q_digits = normalize_cnpj(q)
    results: list[dict[str, Any]] = []
    for row in load_registry_rows():
        cnpj_raw = row.get("CNPJ_FUNDO") or ""
        name = (row.get("DENOM_SOCIAL") or "").strip()
        cnpj_digits = normalize_cnpj(cnpj_raw)
        if not name:
            continue
        match = False
        if q_digits and len(q_digits) >= 4:
            match = q_digits in cnpj_digits
        if not match:
            match = q_lower in name.lower()
        if match:
            results.append({
                "cnpj": cnpj_digits,
                "cnpj_display": cnpj_raw.strip(),
                "name": name,
            })
        if len(results) >= limit:
            break
    with _cache_lock:
        if len(_search_cache) >= _SEARCH_CACHE_MAX:
            _search_cache.clear()
        _search_cache[cache_key] = (now, results)
    return results


def lookup_fund_by_cnpj(cnpj: str) -> dict[str, Any] | None:
    digits = normalize_cnpj(cnpj)
    if len(digits) != 14:
        return None
    for row in load_registry_rows():
        cnpj_raw = row.get("CNPJ_FUNDO") or ""
        if normalize_cnpj(cnpj_raw) == digits:
            return {
                "cnpj": digits,
                "cnpj_display": cnpj_raw.strip(),
                "name": (row.get("DENOM_SOCIAL") or "").strip(),
            }
    return None