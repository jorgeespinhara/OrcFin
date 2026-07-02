"""Per-user data directories and legacy migration."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from core.branding import APP_NAME, BACKUP_SUFFIX, DB_FILENAME

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LEGACY_DATA_DIR = _PROJECT_ROOT / "data"
_LEGACY_CONFIG_FILE = _PROJECT_ROOT / "config" / "settings.json"
_LEGACY_BACKUPS_DIR = _PROJECT_ROOT / "backups"

_migrated = False

_SQLITE_HEADER = b"SQLite format 3\x00"
WINDOWS_DEFAULT_ROOT = Path(r"C:\OrcFin")
_DATA_ROOT_POINTER_NAME = "data_root.txt"


def is_sqlite_database(path: Path) -> bool:
    """True when path looks like a readable SQLite database file."""
    try:
        if not path.is_file() or path.stat().st_size < len(_SQLITE_HEADER):
            return False
        with path.open("rb") as fh:
            return fh.read(len(_SQLITE_HEADER)) == _SQLITE_HEADER
    except OSError:
        return False


def get_bootstrap_dir() -> Path:
    override = os.environ.get("ORCFIN_BOOTSTRAP_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return WINDOWS_DEFAULT_ROOT / "config"
    return get_default_data_root() / "config"


def get_default_data_root() -> Path:
    if os.name == "nt":
        return WINDOWS_DEFAULT_ROOT
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".local" / "share" / "orcfin"


def get_data_root_pointer_path() -> Path:
    return get_bootstrap_dir() / _DATA_ROOT_POINTER_NAME


def read_stored_data_root() -> Path | None:
    pointer = get_data_root_pointer_path()
    if not pointer.is_file():
        return None
    try:
        raw = pointer.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return Path(raw) if raw else None


def write_data_root_pointer(path: Path) -> None:
    bootstrap = get_bootstrap_dir()
    bootstrap.mkdir(parents=True, exist_ok=True)
    get_data_root_pointer_path().write_text(str(path.resolve()), encoding="utf-8")


def get_app_data_dir() -> Path:
    override = os.environ.get("ORCFIN_DATA_DIR")
    if override:
        return Path(override)
    stored = read_stored_data_root()
    if stored is not None:
        return stored
    return get_default_data_root()


def _legacy_windows_appdata_dir() -> Path | None:
    if os.name != "nt":
        return None
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        return None
    return Path(base) / APP_NAME


def _migrate_windows_appdata_if_needed(new_root: Path) -> None:
    old_root = _legacy_windows_appdata_dir()
    if old_root is None or old_root.resolve() == new_root.resolve():
        return
    new_db = new_root / "data" / DB_FILENAME
    if new_db.exists():
        return
    old_db = old_root / "data" / DB_FILENAME
    if not is_sqlite_database(old_db):
        return
    for name in ("data", "config", "backups"):
        src = old_root / name
        if src.is_dir():
            shutil.copytree(src, new_root / name, dirs_exist_ok=True)


def reload_runtime_paths() -> None:
    """Apply a new data root in the running process (onboarding folder picker)."""
    global _migrated
    _migrated = False
    root = get_app_data_dir()
    os.environ["ORCFIN_DATA_DIR"] = str(root)

    import core.db.connection as conn
    import core.settings_store as settings

    new_db = get_database_path()
    conn.DB_PATH = new_db
    conn._DB_PATH = new_db
    settings.CONFIG_FILE = get_config_path()
    migrate_legacy_layout()


def set_data_root(path: Path) -> Path:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_data_root_pointer(root)
    os.environ["ORCFIN_DATA_DIR"] = str(root)
    reload_runtime_paths()
    return root


def get_database_path() -> Path:
    return get_app_data_dir() / "data" / DB_FILENAME


def get_config_path() -> Path:
    return get_app_data_dir() / "config" / "settings.json"


def get_default_backup_dir() -> Path:
    return get_app_data_dir() / "backups"


def legacy_project_data_dir() -> Path:
    return _LEGACY_DATA_DIR


def ensure_app_dirs() -> Path:
    root = get_app_data_dir()
    for name in ("data", "config", "backups"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def migrate_legacy_layout() -> None:
    global _migrated
    if _migrated:
        return
    _migrated = True

    root = get_app_data_dir()
    if not os.environ.get("ORCFIN_DATA_DIR"):
        _migrate_windows_appdata_if_needed(root)
    ensure_app_dirs()
    new_db = get_database_path()
    if not new_db.exists():
        candidate = _LEGACY_DATA_DIR / DB_FILENAME
        if is_sqlite_database(candidate):
            shutil.copy2(candidate, new_db)

    new_cfg = get_config_path()
    if not new_cfg.exists() and _LEGACY_CONFIG_FILE.exists():
        shutil.copy2(_LEGACY_CONFIG_FILE, new_cfg)

    new_backups = get_default_backup_dir()
    if _LEGACY_BACKUPS_DIR.is_dir():
        for backup in _LEGACY_BACKUPS_DIR.glob(f"*{BACKUP_SUFFIX}"):
                dest = new_backups / backup.name
                if not dest.exists():
                    shutil.copy2(backup, dest)


def open_app_data_dir() -> Path:
    root = ensure_app_dirs()
    if os.name == "nt":
        os.startfile(root)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{root}"')
    else:
        os.system(f'xdg-open "{root}"')
    return root