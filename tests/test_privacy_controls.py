"""Privacy controls: offline mode, audit log, data summary."""

from core.ai_gateway import test_connection as verify_provider_connection
from core.audit_log import list_recent_events, log_event
from core.db.connection import get_connection
from core.network_policy import BLOCKED_MESSAGE, external_calls_allowed
from core.privacy import describe_secret_storage, get_local_data_summary
from core.settings_store import DEFAULT_SETTINGS


def test_strict_offline_blocks_external_policy():
    settings = dict(DEFAULT_SETTINGS)
    settings["strict_offline"] = True
    assert not external_calls_allowed(settings)


def test_strict_offline_blocks_ai_test(fresh_db):
    settings = dict(DEFAULT_SETTINGS)
    settings["strict_offline"] = True
    result = verify_provider_connection("deepseek", "fake-key", settings=settings)
    assert result["success"] is False
    assert BLOCKED_MESSAGE in result["error"]
    events = list_recent_events(5)
    assert events
    assert events[0]["event_type"] == "ai_blocked"


def test_audit_log_persists(fresh_db):
    log_event("ai_test", "Evento de teste", provider="deepseek", detail="totais agregados")
    rows = list_recent_events(1)
    assert len(rows) == 1
    assert rows[0]["summary"] == "Evento de teste"
    assert rows[0]["provider"] == "deepseek"


def test_audit_table_exists(fresh_db):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_describe_secret_storage():
    label = describe_secret_storage()
    assert "Chaves de API" in label


def test_local_data_summary(fresh_db, monkeypatch, project_tmp_path):
    monkeypatch.setenv("ORCFIN_DATA_DIR", str(project_tmp_path))
    summary = get_local_data_summary()
    assert summary["data_root"] == str(project_tmp_path)
    assert "database_path" in summary