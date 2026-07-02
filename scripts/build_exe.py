"""Build OrcFin Windows executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Instale PyInstaller: pip install pyinstaller")
        return 1

    from PyInstaller.utils.hooks import collect_data_files

    sep = ";" if sys.platform.startswith("win") else ":"
    assets = f"{ROOT / 'assets'}{sep}assets"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ROOT / "main.py"),
        "--name=OrcFin",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--add-data={assets}",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT / 'scripts'}",
        "--hidden-import=sqlite3",
        "--hidden-import=defusedxml",
        "--hidden-import=defusedxml.ElementTree",
        "--hidden-import=anthropic",
        "--hidden-import=keyring.backends.Windows",
        "--hidden-import=yfinance",
        "--hidden-import=core.integrations.funds.cvm_registry",
        "--hidden-import=core.integrations.funds.cvm_quota",
        "--hidden-import=core.integrations.quotes.yfinance_provider",
        "--hidden-import=core.integrations.quotes.ticker_registry",
        "--hidden-import=core.services.portfolio_service",
        "--hidden-import=ui.investments.view",
    ]
    for src, dest in collect_data_files("flet"):
        cmd.append(f"--add-data={src}{sep}{dest}")
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())