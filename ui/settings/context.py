"""Mutable context passed to settings section builders."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, List
from core.models import Category, Profile

if TYPE_CHECKING:
    from ui.shell import OrcFinApp

@dataclass
class SettingsCtx:
    app: "OrcFinApp"
    profiles: List[Profile]
    categories: List[Category]
