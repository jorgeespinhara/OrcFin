"""Tests for CSV mapper, backup preview and transaction origin."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from core.backup import create_backup, preview_backup
from core.db.schema import init_database
from core.import_parsers.detect import detect_csv_institution
from core.import_parsers.generic_csv import parse_generic_csv, probe_csv_columns, template_to_column_map
from core.import_parsers.pdf_parser import _detect_institution
from core.models import Transaction, TransactionType
from core.transaction_origin import describe_transaction_origin
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction, update_transaction
from core.change_log import list_changes_for_entity


def test_probe_csv_columns():
    content = b"Data;Historico;Valor\n01/01/2026;Teste;-10,00\n"
    cols, sep = probe_csv_columns(content)
    assert "Data" in cols
    assert sep == ";"


def test_template_to_column_map():
    row = {
        "date_col": "Data",
        "desc_col": "Hist",
        "amount_col": "Valor",
        "sep": ";",
    }
    assert template_to_column_map(row)["date_col"] == "Data"


def test_generic_csv_with_explicit_map():
    csv_content = """ColA;ColB;ColC
10/01/2026;Mercado;-50,00
"""
    result = parse_generic_csv(
        csv_content,
        "x.csv",
        column_map={"date_col": "ColA", "desc_col": "ColB", "amount_col": "ColC", "sep": ";"},
    )
    assert len(result.lines) == 1
    assert result.lines[0].amount == Decimal("50.00")


def test_detect_santander_caixa():
    assert detect_csv_institution("santander extrato", "santander_jan.csv") == "santander"
    assert detect_csv_institution("caixa economica", "caixa.csv") == "caixa"
    assert _detect_institution("FATURA SANTANDER") == "Santander"
    assert _detect_institution("CAIXA ECONOMICA FEDERAL") == "Caixa"


def test_preview_backup_sandbox(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "orcfin.db"
    backup_dir = project_tmp_path / "backups"
    monkeypatch.setattr("core.db.connection._DB_PATH", db_path)
    init_database()

    profile = create_profile("Preview")
    cat = create_category("Gasto", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 3, 15),
            description="Sandbox",
            amount=Decimal("25"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )
    path = create_backup(backup_dir)
    info = preview_backup(path)
    assert info["valid"]
    assert info["transaction_count"] >= 1
    assert "Preview" in info["profile_names"]
    assert info["date_min"] == "2026-03-15"


def test_transaction_origin_and_change_log(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "t.db")
    init_database()
    profile = create_profile("Audit")
    cat = create_category("Food", TransactionType.EXPENSE)
    tx = create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date(2026, 6, 1),
            description="Manual lunch",
            amount=Decimal("30"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
        )
    )
    origin = describe_transaction_origin(tx)
    assert origin["kind"] == "manual"
    tx.description = "Manual lunch updated"
    update_transaction(tx)
    changes = list_changes_for_entity("transaction", tx.id)
    assert changes and changes[0]["action"] == "update"