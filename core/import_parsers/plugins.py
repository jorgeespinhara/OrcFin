"""Load optional user-provided import parsers from the data directory."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

from core.import_parsers.registry import PARSERS
from core.paths import get_app_data_dir

_loaded = False


def register_parser(parser_id: str, meta: dict[str, Any]) -> None:
    PARSERS[parser_id] = meta


def get_plugins_dir() -> Path:
    return get_app_data_dir() / "plugins" / "import_parsers"


def load_user_plugins() -> int:
    global _loaded
    if _loaded:
        return 0
    _loaded = True
    folder = get_plugins_dir()
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"orcfin_plugin_{path.stem}", path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue
        hook: Callable[..., None] | None = getattr(module, "register", None)
        if callable(hook):
            hook(register_parser)
            count += 1
    return count