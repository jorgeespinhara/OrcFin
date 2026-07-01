"""Backup protection score for settings UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.backup import _backup_dir_from_settings, find_latest_backup, list_backups
from core.paths import get_app_data_dir


def _backup_age_days(settings: dict, latest: Path | None) -> int | None:
    last_at = settings.get("last_backup_at")
    if last_at:
        try:
            return max(0, (datetime.now() - datetime.fromisoformat(last_at)).days)
        except ValueError:
            pass
    if latest:
        return max(0, int((datetime.now().timestamp() - latest.stat().st_mtime) // 86400))
    return None


def _same_folder_as_data(backup_dir: Path) -> bool:
    try:
        data = get_app_data_dir().resolve()
        folder = backup_dir.resolve()
        return folder == data or data in folder.parents or folder in data.parents
    except OSError:
        return False


def assess_backup_health(settings: dict | None = None) -> dict[str, Any]:
    settings = settings or {}
    folder = _backup_dir_from_settings(settings)
    latest = find_latest_backup(folder)
    age = _backup_age_days(settings, latest)
    same_folder = _same_folder_as_data(folder)
    auto = bool(settings.get("backup_on_close")) or int(settings.get("backup_interval_days") or 0) > 0

    tips: list[str] = []
    if not latest:
        tips.append("Crie o primeiro backup agora.")
    if age is not None and age > 14:
        tips.append(f"Último backup há {age} dias.")
    if same_folder:
        tips.append("Use pasta externa (pendrive ou outro disco) para maior segurança.")
    if not auto:
        tips.append("Ative backup ao fechar ou backup automático.")

    if not latest or (age is not None and age > 30):
        level = "critico"
    elif (age is not None and age > 14) or same_folder or not auto:
        level = "atencao"
    elif age is not None and age <= 7 and auto and not same_folder:
        level = "otimo"
    else:
        level = "bom"

    labels = {"otimo": "Ótimo", "bom": "Bom", "atencao": "Atenção", "critico": "Crítico"}
    return {
        "level": level,
        "label": labels[level],
        "age_days": age,
        "backup_count": len(list_backups(folder)),
        "same_folder_as_data": same_folder,
        "recommendations": tips[:3],
        "latest_name": latest.name if latest else None,
        "folder": str(folder),
    }