"""Build OrcFin PRO Windows executable with PyInstaller (pywebview + FastAPI + React)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HIDDEN_IMPORTS = (
    "sqlite3",
    "defusedxml",
    "defusedxml.ElementTree",
    "anthropic",
    "keyring.backends.Windows",
    "yfinance",
    "webview",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "api.server",
    "api.routes_personal",
    "api.routes_mei",
    "core.integrations.funds.cvm_registry",
    "core.integrations.funds.cvm_quota",
    "core.integrations.quotes.yfinance_provider",
    "core.integrations.quotes.ticker_registry",
    "core.services.portfolio_service",
    "core.i18n",
)


def _pyinstaller_cmd() -> list[str]:
    frontend_dist = ROOT / "frontend" / "dist"
    if not (frontend_dist / "index.html").exists():
        raise FileNotFoundError(
            f"Build do frontend não encontrado em {frontend_dist}. "
            "Execute 'npm run build' dentro de frontend/ antes de empacotar."
        )

    assets = ROOT / "assets"
    icon = assets / "orcfin.ico"
    sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ROOT / "main.py"),
        "--name",
        "OrcFin",
        "--icon",
        str(icon),
        "--onedir",
        "--noconsole",
        "--noconfirm",
        "--distpath",
        str(ROOT / "dist"),
        "--add-data",
        f"{frontend_dist}{sep}frontend/dist",
        "--add-data",
        f"{assets}{sep}assets",
        "--add-data",
        f"{ROOT / 'core' / 'i18n' / 'locales'}{sep}core/i18n/locales",
        "--exclude-module",
        "flet",
        "--exclude-module",
        "flet_desktop",
        "--exclude-module",
        "ui",
    ]
    for mod in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", mod])
    return cmd


def main() -> int:
    cmd = _pyinstaller_cmd()
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
