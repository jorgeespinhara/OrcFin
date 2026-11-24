"""
OrcFin: Orçamento Financeiro (v1.0.0 PRO)
Entry point. Run with: python main.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from core.diagnostics import install_diagnostics_handler


def get_assets_dir() -> Path:
    default = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"
    return Path(os.environ.get("FLET_ASSETS_DIR", str(default))).resolve()


def main() -> None:
    install_diagnostics_handler()
    if "--legacy" in sys.argv:
        import flet as ft
        from ui.app import start

        ft.run(start, assets_dir=get_assets_dir())
        return

    from desktop import main as run_desktop

    run_desktop()


if __name__ == "__main__":
    main()
