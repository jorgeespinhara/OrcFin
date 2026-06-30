"""Pytest configuration — use project-local temp dir (avoids Windows AppData permission issues)."""

import uuid
from pathlib import Path

import pytest

_PROJECT_TMP = Path(__file__).resolve().parent.parent / ".pytest_tmp"


def pytest_configure(config):
    _PROJECT_TMP.mkdir(parents=True, exist_ok=True)
    cache_dir = _PROJECT_TMP / "pytest_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    config.option.cache_dir = str(cache_dir)
    if not getattr(config.option, "basetemp", None):
        config.option.basetemp = str(_PROJECT_TMP)


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


@pytest.fixture
def project_tmp_path():
    """Writable temp directory inside the project workspace."""
    path = _PROJECT_TMP / "cases"
    path.mkdir(parents=True, exist_ok=True)
    case_dir = path / f"case-{uuid.uuid4().hex}"
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir