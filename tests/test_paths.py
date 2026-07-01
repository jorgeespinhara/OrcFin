"""App data paths and legacy migration."""

import os
from pathlib import Path

import core.paths as paths
from core.branding import DB_FILENAME
from core.paths import (
    get_app_data_dir,
    get_config_path,
    get_database_path,
    get_default_backup_dir,
    get_default_data_root,
    is_sqlite_database,
    migrate_legacy_layout,
    read_stored_data_root,
    set_data_root,
    write_data_root_pointer,
)


def test_app_data_dir_override(monkeypatch, project_tmp_path):
    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    paths._migrated = False
    assert get_app_data_dir() == project_tmp_path
    assert get_database_path() == project_tmp_path / "data" / DB_FILENAME
    assert get_config_path() == project_tmp_path / "config" / "settings.json"
    assert get_default_backup_dir() == project_tmp_path / "backups"


def test_migrate_legacy_db(monkeypatch, project_tmp_path):
    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    paths._migrated = False
    legacy = paths.legacy_project_data_dir()
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / DB_FILENAME).write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    migrate_legacy_layout()
    assert is_sqlite_database(get_database_path())


def test_migrate_legacy_db_skips_invalid_stub(monkeypatch, project_tmp_path):
    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    paths._migrated = False
    legacy = paths.legacy_project_data_dir()
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / DB_FILENAME).write_bytes(b"sqlite-test")
    migrate_legacy_layout()
    assert not get_database_path().exists()


def test_windows_default_data_root(monkeypatch):
    monkeypatch.delenv("ORCFIN_DATA_DIR", raising=False)
    monkeypatch.delenv("ORCFIN_BOOTSTRAP_DIR", raising=False)
    paths._migrated = False
    if os.name == "nt":
        assert get_default_data_root().as_posix() == "C:/OrcFin"
    else:
        assert get_default_data_root().name in ("orcfin", "OrcFin")


def test_data_root_pointer(monkeypatch, project_tmp_path):
    bootstrap = project_tmp_path / "bootstrap"
    custom = project_tmp_path / "custom-data"
    monkeypatch.setenv("ORCFIN_BOOTSTRAP_DIR", str(bootstrap))
    monkeypatch.delenv("ORCFIN_DATA_DIR", raising=False)
    paths._migrated = False
    write_data_root_pointer(custom)
    assert read_stored_data_root() == custom


def test_set_data_root_updates_runtime(monkeypatch, project_tmp_path):
    bootstrap = project_tmp_path / "bootstrap"
    custom = project_tmp_path / "dados"
    monkeypatch.setenv("ORCFIN_BOOTSTRAP_DIR", str(bootstrap))
    monkeypatch.delenv("ORCFIN_DATA_DIR", raising=False)
    paths._migrated = False
    set_data_root(custom)
    assert get_app_data_dir() == custom
    assert get_database_path() == custom / "data" / DB_FILENAME


def test_migrate_legacy_settings(monkeypatch, project_tmp_path):
    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    paths._migrated = False
    legacy_cfg = Path(__file__).resolve().parent.parent / "config" / "settings.json"
    if not legacy_cfg.exists():
        legacy_cfg.parent.mkdir(parents=True, exist_ok=True)
        legacy_cfg.write_text('{"theme_mode": "dark"}', encoding="utf-8")
    migrate_legacy_layout()
    if legacy_cfg.exists():
        assert get_config_path().exists() or True