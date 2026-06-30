"""Tests for local-first P0 features: duplicates, backup, search."""

from datetime import date
from decimal import Decimal

from core.backup import create_backup, inspect_backup, list_backups, maybe_auto_backup, prune_backups
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction, search_transactions
from core.db.schema import init_database
from core.models import Transaction, TransactionType
from core.services.import_service import prepare_import


def test_import_flags_duplicate_transactions(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()

    profile = create_profile("Pessoal")
    cat = create_category("Mercado", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 6, 10),
            description="IFOOD *PEDIDO",
            amount=Decimal("45.90"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )

    csv = b"date,title,amount\n2026-06-10,IFOOD *PEDIDO,-45.90\n2026-06-11,UBER,-20.00\n"
    result = prepare_import(csv, "fatura.csv", profile.id)

    dupes = [ln for ln in result.lines if ln.is_duplicate]
    assert len(dupes) == 1
    assert dupes[0].selected is False
    assert any("desmarcados" in w for w in result.warnings)


def test_search_transactions_matches_description_and_notes(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()

    profile = create_profile("Busca")
    cat = create_category("Geral", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 5, 1),
            description="Netflix assinatura",
            amount=Decimal("55.90"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
            notes="recorrente",
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 5, 2),
            description="Supermercado",
            amount=Decimal("120"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )

    by_desc = search_transactions("netflix", profile_id=profile.id)
    by_note = search_transactions("recorrente", profile_id=profile.id)

    assert len(by_desc) == 1
    assert by_desc[0].description == "Netflix assinatura"
    assert len(by_note) == 1


def test_backup_inspect_and_auto_schedule(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    backup_dir = project_tmp_path / "backups"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()

    profile = create_profile("Backup")
    cat = create_category("Teste", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 6, 1),
            description="Compra teste",
            amount=Decimal("10"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )

    path = create_backup(backup_dir)
    info = inspect_backup(path)
    assert info["transaction_count"] >= 1
    assert info["profile_count"] >= 1
    assert info["created_at"]

    settings = {
        "backup_dir": str(backup_dir),
        "backup_interval_days": 1,
        "backup_retention_count": 2,
        "last_backup_at": None,
    }
    second = maybe_auto_backup(settings)
    assert second is not None
    assert settings["last_backup_at"]
    assert len(list_backups(backup_dir)) >= 2
    prune_backups(backup_dir, keep=1)
    assert len(list_backups(backup_dir)) == 1