"""Pytest configuration — isolated project-local temp dir and runtime env."""

import shutil
import sys
import types
import uuid
from pathlib import Path

import pytest

_PROJECT_TMP = Path(__file__).resolve().parent.parent / ".pytest_tmp"


def pytest_configure(config):
    _PROJECT_TMP.mkdir(parents=True, exist_ok=True)
    if not getattr(config.option, "basetemp", None):
        config.option.basetemp = str(_PROJECT_TMP)


@pytest.fixture
def project_tmp_path():
    """Writable temp directory inside the project workspace, cleaned up after test."""
    path = _PROJECT_TMP / "cases"
    path.mkdir(parents=True, exist_ok=True)
    case_dir = path / f"case-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def _isolate_runtime_env(project_tmp_path, monkeypatch):
    """Keep tests isolated from real user data, repo exports, and OS keyring."""
    import core.data_export as data_export
    import core.mei_calendar as mei_calendar
    import core.paths as paths
    import core.secrets as secrets

    app_data = project_tmp_path / "app_data"
    bootstrap = project_tmp_path / "bootstrap"
    exports_dir = project_tmp_path / "exports"

    monkeypatch.setenv("ORCFIN_DATA_DIR", str(app_data))
    monkeypatch.setenv("ORCFIN_BOOTSTRAP_DIR", str(bootstrap))
    monkeypatch.setattr(paths, "_migrated", True)
    monkeypatch.setattr(data_export, "_EXPORT_DIR", exports_dir)
    monkeypatch.setattr(mei_calendar, "_EXPORT_DIR", exports_dir)

    # In-memory fake keyring so tests never read/write the real OS Credential Manager
    store: dict[tuple[str, str], str] = {}
    fake_keyring = types.ModuleType("keyring")
    fake_keyring.get_password = lambda svc, name: store.get((svc, name))  # type: ignore[attr-defined]
    fake_keyring.set_password = lambda svc, name, val: store.__setitem__((svc, name), val)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)
    monkeypatch.setattr(secrets, "_uses_system_keyring", None)
    monkeypatch.setattr(secrets, "_legacy_key_used", False)
    if hasattr(secrets, "clear_master_key_cache"):
        secrets.clear_master_key_cache()
    yield
    if hasattr(secrets, "clear_master_key_cache"):
        secrets.clear_master_key_cache()


@pytest.fixture(autouse=True)
def _reset_locale():
    """Keep default locale pt-BR so tests don't leak en-US/es-ES from i18n checks."""
    from core.i18n import apply_locale_settings, clear_locale_cache

    clear_locale_cache()
    apply_locale_settings(locale="pt-BR", country_profile="BR", currency="BRL")
    yield
    clear_locale_cache()
    apply_locale_settings(locale="pt-BR", country_profile="BR", currency="BRL")


@pytest.fixture
def fresh_db(project_tmp_path, monkeypatch):
    """Isolated SQLite database for a single test."""
    from core.db.schema import init_database

    db_path = project_tmp_path / "test.db"
    if db_path.exists():
        db_path.unlink()
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()
    yield db_path