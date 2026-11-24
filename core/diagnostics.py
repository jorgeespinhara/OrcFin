"""Sanitized diagnostics report for offline support (zero PII / zero financial data)."""

from __future__ import annotations

import logging
import platform
import re
import sqlite3
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

from core.branding import APP_NAME, APP_VERSION
from core.db.connection import SCHEMA_VERSION
from core.paths import get_app_data_dir
from core.settings_store import load_settings

_MAX_RECORDS = 50
_ring_handler: "_RingLogHandler | None" = None

_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[CNPJ]"),
    (re.compile(r"(?i)(?:sk-|AIza|ghp_|xox[baprs]-)[A-Za-z0-9_\-]{8,}"), "[TOKEN]"),
    (re.compile(r"(?:R\$|\$|€)\s*-?\d[\d.,]*"), "[AMOUNT]"),
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+"), r"C:\\Users\\[USER]"),
    (re.compile(r"/(?:home|Users)/[^/\s]+"), "/Users/[USER]"),
)


def scrub_text(text: str) -> str:
    """Remove PII, tokens, amounts, and OS usernames from diagnostic text."""
    out = str(text or "")
    for pattern, replacement in _SCRUB_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


class _RingLogHandler(logging.Handler):
    def __init__(self, maxlen: int = _MAX_RECORDS):
        super().__init__(level=logging.WARNING)
        self.records: deque[str] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
            msg = scrub_text(self.format(record))
            self.records.append(f"[{ts}] {record.levelname} {record.name}: {msg}")
        except Exception:
            pass


def install_diagnostics_handler() -> None:
    """Attach the in-memory warning/error ring buffer once to the root logger."""
    global _ring_handler
    if _ring_handler is not None:
        return
    handler = _RingLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)
    _ring_handler = handler


def get_recent_errors() -> list[str]:
    if _ring_handler is None:
        return []
    return list(_ring_handler.records)


def build_diagnostics_report() -> str:
    """Build a human-readable, privacy-safe diagnostics summary."""
    settings = load_settings()
    try:
        import flet

        flet_version = getattr(flet, "__version__", "unknown")
    except Exception:
        flet_version = "unavailable"

    lines = [
        f"{APP_NAME} - Sanitized Diagnostics Report",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "[Environment]",
        f"App version: {APP_VERSION}",
        f"Schema version: {SCHEMA_VERSION}",
        f"Python: {sys.version.split()[0]}",
        f"SQLite: {sqlite3.sqlite_version}",
        f"Flet: {flet_version}",
        f"OS: {platform.system()} {platform.release()} ({platform.machine()})",
        "",
        "[Safe Preferences]",
        f"locale: {settings.get('locale', 'pt-BR')}",
        f"country_profile: {settings.get('country_profile', 'BR')}",
        f"currency: {settings.get('currency', 'BRL')}",
        f"theme_mode: {settings.get('theme_mode', 'dark')}",
        f"setup_mode: {settings.get('setup_mode', 'personal')}",
        f"strict_offline: {bool(settings.get('strict_offline', False))}",
        f"backup_on_close: {bool(settings.get('backup_on_close', False))}",
        "",
        "[Recent Warnings & Errors (Sanitized)]",
    ]
    recent = get_recent_errors()
    if recent:
        lines.extend(recent)
    else:
        lines.append("(none recorded in this session)")
    return "\n".join(lines) + "\n"


def export_diagnostics(dest_dir: Path | None = None) -> Path:
    """Write the sanitized diagnostics report to a .txt file and return its path."""
    target_dir = dest_dir or (get_app_data_dir() / "exports")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = target_dir / f"orcfin_diagnostics_{stamp}.txt"
    out_path.write_text(build_diagnostics_report(), encoding="utf-8", newline="\n")
    return out_path
