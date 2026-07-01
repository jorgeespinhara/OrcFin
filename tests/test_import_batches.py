"""Import batches: tracking and rollback."""

from datetime import date
from decimal import Decimal

from core.db.connection import get_connection
from core.db.repositories.categories import get_categories_for_profile
from core.db.repositories.import_batches import (
    STATUS_ROLLED_BACK,
    list_import_batches,
    rollback_import_batch,
)
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import create_transaction, get_transactions
from core.import_parsers.models import ParseResult, ParsedStatementLine
from core.models import Transaction, TransactionType
from core.services.import_service import commit_import


def _expense_category_id(profile_id: int) -> int:
    for cat in get_categories_for_profile(profile_id):
        if cat.type == TransactionType.EXPENSE:
            return cat.id
    raise AssertionError("missing expense category")


def _sample_result(profile_id: int, *, filename: str = "extrato.csv") -> ParseResult:
    cat_id = _expense_category_id(profile_id)
    return ParseResult(
        institution="Nubank",
        filename=filename,
        bank="Nubank",
        source_type="bank_statement",
        file_hash="abc123",
        lines=[
            ParsedStatementLine(
                date=date(2026, 6, 10),
                description="Mercado",
                amount=Decimal("42.50"),
                tx_type=TransactionType.EXPENSE,
                suggested_category_id=cat_id,
            ),
            ParsedStatementLine(
                date=date(2026, 6, 11),
                description="Farmácia",
                amount=Decimal("18.00"),
                tx_type=TransactionType.EXPENSE,
                suggested_category_id=cat_id,
                selected=False,
            ),
        ],
    )


def test_commit_import_creates_batch(fresh_db):
    profile_id = get_all_profiles()[0].id
    result = _sample_result(profile_id)
    count, batch_id = commit_import(result, profile_id)
    assert count == 1
    assert batch_id is not None

    batches = list_import_batches(profile_id)
    assert len(batches) == 1
    assert batches[0]["rows_total"] == 2
    assert batches[0]["rows_imported"] == 1
    assert batches[0]["rows_skipped"] == 1
    assert batches[0]["filename"] == "extrato.csv"


def test_rollback_removes_only_batch_transactions(fresh_db):
    profile_id = get_all_profiles()[0].id
    cat_id = _expense_category_id(profile_id)
    manual = create_transaction(
        Transaction(
            profile_id=profile_id,
            date=date(2026, 6, 1),
            description="Lançamento manual",
            amount=Decimal("99.00"),
            category_id=cat_id,
            type=TransactionType.EXPENSE,
        )
    )

    result = _sample_result(profile_id)
    count, batch_id = commit_import(result, profile_id)
    assert count == 1

    removed = rollback_import_batch(batch_id, profile_id=profile_id)
    assert removed == 1

    txs = get_transactions(profile_id=profile_id)
    assert len(txs) == 1
    assert txs[0].id == manual.id
    assert txs[0].import_batch_id is None

    batches = list_import_batches(profile_id)
    assert batches[0]["status"] == STATUS_ROLLED_BACK


def test_import_batches_table_exists(fresh_db):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='import_batches'"
        ).fetchone()
        assert row is not None
        col = conn.execute("PRAGMA table_info(transactions)").fetchall()
        names = {r[1] for r in col}
        assert "import_batch_id" in names
    finally:
        conn.close()