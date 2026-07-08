"""Build OrcFin Windows executable with flet pack (bundles flet_desktop runtime)."""

from __future__ import annotations

import shutil
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
    "core.integrations.funds.cvm_registry",
    "core.integrations.funds.cvm_quota",
    "core.integrations.quotes.yfinance_provider",
    "core.integrations.quotes.ticker_registry",
    "core.services.portfolio_service",
    "ui.investments.view",
)


def _flet_pack_cmd() -> list[str]:
    sys.path.insert(0, str(ROOT))
    from core.branding import APP_NAME, APP_SUBTITLE, APP_VERSION

    assets = ROOT / "assets"
    icon = assets / "orcfin.ico"
    cmd = [
        "flet",
        "pack",
        str(ROOT / "main.py"),
        "--name",
        "OrcFin",
        "--icon",
        str(icon),
        "-D",
        "--distpath",
        str(ROOT / "dist"),
        "--product-name",
        APP_NAME,
        "--file-description",
        APP_SUBTITLE,
        "--product-version",
        APP_VERSION,
        "--add-data",
        f"{assets}:assets",
        "-y",
    ]
    for mod in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", mod])
    return cmd


def main() -> int:
    if shutil.which("flet") is None:
        print("Instale o Flet CLI: pip install flet-desktop (inclui flet-cli para flet pack)")
        return 1
    try:
        import flet_desktop  # noqa: F401
    except ImportError:
        print("Instale flet-desktop: pip install flet-desktop")
        return 1

    cmd = _flet_pack_cmd()
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())