"""Backup health score."""

from datetime import datetime, timedelta

from core.backup import create_backup
from core.backup_health import assess_backup_health
from core.settings_store import DEFAULT_SETTINGS


def test_backup_health_critico_without_backup(fresh_db, project_tmp_path, monkeypatch):
    backup_dir = project_tmp_path / "backups"
    backup_dir.mkdir()
    settings = dict(DEFAULT_SETTINGS)
    settings["backup_dir"] = str(backup_dir)
    health = assess_backup_health(settings)
    assert health["level"] == "critico"
    assert health["backup_count"] == 0


def test_backup_health_improves_after_backup(fresh_db, project_tmp_path, monkeypatch):
    backup_dir = project_tmp_path / "backups"
    backup_dir.mkdir()
    create_backup(backup_dir)
    settings = dict(DEFAULT_SETTINGS)
    settings["backup_dir"] = str(backup_dir)
    settings["backup_on_close"] = True
    settings["last_backup_at"] = datetime.now().isoformat(timespec="seconds")
    health = assess_backup_health(settings)
    assert health["level"] in ("bom", "otimo", "atencao")
    assert health["backup_count"] >= 1


def test_backup_health_warns_old_backup(fresh_db, project_tmp_path):
    backup_dir = project_tmp_path / "backups"
    backup_dir.mkdir()
    create_backup(backup_dir)
    settings = dict(DEFAULT_SETTINGS)
    settings["backup_dir"] = str(backup_dir)
    old = (datetime.now() - timedelta(days=20)).isoformat(timespec="seconds")
    settings["last_backup_at"] = old
    health = assess_backup_health(settings)
    assert health["level"] in ("atencao", "critico")