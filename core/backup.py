"""Encrypted local backup (SQLite + settings)."""

from __future__ import annotations

import base64
import json
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.branding import APP_NAME, BACKUP_DB_ARCHIVE, BACKUP_SUFFIX
from core.change_log import log_change
from core.db.connection import _resolve_db_path
from core.paths import get_config_path, get_default_backup_dir
from core.secrets import decrypt_secret, encrypt_secret


def _default_backup_dir() -> Path:
    return get_default_backup_dir()


def _db_path() -> Path:
    return _resolve_db_path()


def _db_archive_name() -> str:
    return _db_path().name


def _backup_dir_from_settings(settings: Optional[dict] = None) -> Path:
    if settings and settings.get("backup_dir"):
        return Path(settings["backup_dir"])
    return _default_backup_dir()


def list_backups(directory: Optional[Path] = None) -> List[Path]:
    folder = Path(directory) if directory else _default_backup_dir()
    if not folder.exists():
        return []
    files = list(folder.glob(f"*{BACKUP_SUFFIX}"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def prune_backups(directory: Optional[Path] = None, keep: int = 7) -> int:
    backups = list_backups(directory)
    removed = 0
    for old in backups[keep:]:
        old.unlink(missing_ok=True)
        removed += 1
    return removed


def _safe_extractall(zf: zipfile.ZipFile, extract_dir: Path) -> None:
    base = extract_dir.resolve()
    for member in zf.infolist():
        target = (extract_dir / member.filename).resolve()
        try:
            target.relative_to(base)
        except ValueError as exc:
            raise ValueError(f"Invalid backup archive path: {member.filename}") from exc
        zf.extract(member, extract_dir)


def _resolve_backup_db(extract_dir: Path) -> Path | None:
    db_src = extract_dir / BACKUP_DB_ARCHIVE
    if not db_src.exists():
        db_candidates = list(extract_dir.glob("*.db"))
        db_src = db_candidates[0] if db_candidates else None
    return db_src if db_src and db_src.exists() else None


@contextmanager
def _extract_backup_temp(backup_path: Path) -> Iterator[tuple[Path, Path | None, dict[str, Any]]]:
    """Decrypt backup to an isolated temporary directory and always clean up."""
    backup_path = Path(backup_path)
    token = backup_path.read_text(encoding="utf-8")
    raw = base64.b64decode(decrypt_secret(token))
    with tempfile.TemporaryDirectory(prefix="orcfin_bkp_") as tmp_name:
        tmp_dir = Path(tmp_name)
        tmp_zip = tmp_dir / "archive.zip"
        tmp_zip.write_bytes(raw)
        extract_dir = tmp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            _safe_extractall(zf, extract_dir)
        manifest: dict[str, Any] = {}
        manifest_path = extract_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        yield extract_dir, _resolve_backup_db(extract_dir), manifest


def _query_backup_db(db_src: Path) -> dict[str, Any]:
    conn = sqlite3.connect(db_src)
    conn.row_factory = sqlite3.Row
    try:
        tx_filter = "deleted_at IS NULL"
        try:
            conn.execute("SELECT deleted_at FROM transactions LIMIT 1")
        except sqlite3.OperationalError:
            tx_filter = "1=1"
        tx_count = conn.execute(f"SELECT COUNT(*) FROM transactions WHERE {tx_filter}").fetchone()[0]
        profile_count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        profiles = [
            row["name"]
            for row in conn.execute("SELECT name FROM profiles ORDER BY id").fetchall()
        ]
        period = conn.execute(
            f"SELECT MIN(date) AS dmin, MAX(date) AS dmax FROM transactions WHERE {tx_filter}"
        ).fetchone()
        schema = conn.execute("PRAGMA user_version").fetchone()[0]
        return {
            "transaction_count": int(tx_count or 0),
            "profile_count": int(profile_count or 0),
            "profile_names": profiles,
            "date_min": period["dmin"],
            "date_max": period["dmax"],
            "schema_version": int(schema or 0),
        }
    finally:
        conn.close()


def _snapshot_sqlite_db(src_db: Path, dst_db: Path) -> None:
    """Create a WAL-safe consistent SQLite snapshot using the Online Backup API."""
    src_conn = sqlite3.connect(src_db)
    dst_conn = sqlite3.connect(dst_db)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def _remove_wal_sidecars(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass


def inspect_backup(backup_path: Path) -> Dict[str, Any]:
    """Read backup metadata without restoring."""
    info = preview_backup(backup_path)
    return {
        "filename": info["filename"],
        "file_size": info["file_size"],
        "created_at": info["created_at"],
        "transaction_count": info["transaction_count"],
        "profile_count": info["profile_count"],
    }


def preview_backup(backup_path: Path) -> Dict[str, Any]:
    """Sandbox read of backup contents — never touches live data."""
    backup_path = Path(backup_path)
    info: Dict[str, Any] = {
        "filename": backup_path.name,
        "file_size": backup_path.stat().st_size,
        "created_at": None,
        "transaction_count": 0,
        "profile_count": 0,
        "profile_names": [],
        "date_min": None,
        "date_max": None,
        "schema_version": None,
        "valid": False,
    }
    with _extract_backup_temp(backup_path) as (_extract_dir, db_src, manifest):
        info["created_at"] = manifest.get("created_at")
        if db_src:
            stats = _query_backup_db(db_src)
            info.update(stats)
            info["valid"] = True
    return info


def maybe_auto_backup(settings: dict) -> Optional[Path]:
    """Create backup when interval elapsed. Updates settings['last_backup_at'] in place."""
    interval = int(settings.get("backup_interval_days") or 0)
    if interval <= 0:
        return None
    last = settings.get("last_backup_at")
    if last:
        try:
            if datetime.now() - datetime.fromisoformat(last) < timedelta(days=interval):
                return None
        except ValueError:
            pass
    dest = _backup_dir_from_settings(settings)
    path = create_backup(dest)
    prune_backups(dest, int(settings.get("backup_retention_count") or 7))
    settings["last_backup_at"] = datetime.now().isoformat(timespec="seconds")
    return path


def create_backup(destination_dir: Optional[Path] = None) -> Path:
    """Create AES-encrypted backup archive using a WAL-safe SQLite snapshot."""
    dest = Path(destination_dir) if destination_dir else _default_backup_dir()
    dest.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    db_arc = _db_archive_name()

    manifest = {
        "created_at": datetime.now().isoformat(),
        "version": 1,
        "app": APP_NAME,
        "files": [],
    }

    with tempfile.TemporaryDirectory(prefix="orcfin_bkp_create_") as tmp_name:
        tmp_dir = Path(tmp_name)
        tmp_zip = tmp_dir / f"backup_{stamp}.zip"
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            db_file = _db_path()
            if db_file.exists():
                snap_db = tmp_dir / db_arc
                try:
                    _snapshot_sqlite_db(db_file, snap_db)
                    zf.write(snap_db, arcname=db_arc)
                except sqlite3.DatabaseError:
                    zf.write(db_file, arcname=db_arc)
                manifest["files"].append(db_arc)
            cfg = get_config_path()
            if cfg.exists():
                zf.write(cfg, arcname="settings.json")
                manifest["files"].append("settings.json")
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        raw = tmp_zip.read_bytes()

    token = encrypt_secret(base64.b64encode(raw).decode("ascii"))
    out = dest / f"orcfin_backup_{stamp}{BACKUP_SUFFIX}"
    out.write_text(token, encoding="utf-8")
    log_change("backup", "create", f"Backup criado: {out.name}")
    return out


def restore_backup(backup_path: Path) -> None:
    """Restore database and settings from encrypted backup."""
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise FileNotFoundError(str(backup_path))

    with _extract_backup_temp(backup_path) as (extract_dir, db_src, _manifest):
        settings_src = extract_dir / "settings.json"
        if db_src and db_src.exists():
            dest_db = _db_path()
            dest_db.parent.mkdir(parents=True, exist_ok=True)
            _remove_wal_sidecars(dest_db)
            shutil.copy2(db_src, dest_db)
            _remove_wal_sidecars(dest_db)
            from core.db.schema import init_database

            init_database()
        if settings_src.exists():
            cfg_dest = get_config_path()
            cfg_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(settings_src, cfg_dest)
        log_change("backup", "restore", f"Backup restaurado: {backup_path.name}")


def find_latest_backup(directory: Optional[Path] = None) -> Optional[Path]:
    backups = list_backups(directory)
    return backups[0] if backups else None
