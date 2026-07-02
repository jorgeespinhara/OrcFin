"""
OrcFin: Orçamento Financeiro
Entry point. Run with: python main.py
"""

import os
from pathlib import Path

import flet as ft
from ui.app import start


def get_assets_dir() -> Path:
    default = Path(__file__).parent / "assets"
    return Path(os.environ.get("FLET_ASSETS_DIR", str(default))).resolve()


if __name__ == "__main__":
    ft.run(start, assets_dir=get_assets_dir())