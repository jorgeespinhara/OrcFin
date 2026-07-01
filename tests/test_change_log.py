"""Local change log."""

from core.change_log import list_recent_changes, log_change


def test_change_log_records(fresh_db):
    log_change("import", "commit", "Teste de importação", entity_id=1)
    rows = list_recent_changes(5)
    assert rows
    assert rows[0]["entity"] == "import"