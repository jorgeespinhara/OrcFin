"""
OrcFin: Orçamento Financeiro
Entry point. Run with: python main.py
"""

from pathlib import Path

import flet as ft
from ui.app import start

_ASSETS_DIR = Path(__file__).parent / "assets"


if __name__ == "__main__":
    ft.run(start, assets_dir=str(_ASSETS_DIR))