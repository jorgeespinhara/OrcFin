from decimal import Decimal
from datetime import date

import pytest

from core.import_parsers.nubank import parse_nubank_csv
from core.import_parsers.generic_csv import parse_generic_csv
from core.import_parsers.pdf_parser import _parse_lines_from_text, _detect_institution
from core.import_parsers import parse_statement_file
from core.engine.categorization import (
    AUTO_CAT_MARKER,
    append_auto_cat_marker,
    create_rule,
    strip_system_notes,
    suggest_category,
)
from core.services.import_service import create_installment_plan
from core.db.repositories.budgets import set_budget
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import get_transactions
from core.db.schema import init_database
from core.models import TransactionType
from core.engine.budget_alerts import check_budget_impact


def test_nubank_csv_parse(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "t.db")
    init_database()

    csv_content = """date,title,amount
2026-01-10,IFOOD *PEDIDO,-45.90
2026-01-11,PIX RECEBIDO,1200.00
"""
    result = parse_nubank_csv(csv_content, "fatura.csv")
    assert result.institution == "Nubank"
    assert len(result.lines) == 2
    assert result.lines[0].tx_type == TransactionType.EXPENSE
    assert result.lines[0].amount == Decimal("45.90")
    assert result.lines[1].tx_type == TransactionType.INCOME


def test_generic_csv_parse():
    csv_content = """Data;Histórico;Valor
10/01/2026;Supermercado;-150,50
11/01/2026;Salário;3000,00
"""
    result = parse_generic_csv(csv_content, "extrato.csv")
    assert result.institution == "CSV Genérico"
    assert len(result.lines) == 2
    assert result.lines[0].amount == Decimal("150.50")


def test_pdf_text_parsing():
    text = """
    BTG PACTUAL
    10/06/2026 MERCADO XYZ R$ 45,90
    11/06/2026 PIX RECEBIDO R$ 100,00
    """
    assert _detect_institution(text) == "BTG"
    lines, _ = _parse_lines_from_text(text)
    assert len(lines) >= 2
    assert lines[0].tx_type == TransactionType.EXPENSE


def test_pdf_desc_date_pattern():
    text = "COMPRA LOJA ABC 15/06/2026 R$ 1.200,00"
    lines, _ = _parse_lines_from_text(text)
    assert len(lines) == 1
    assert "LOJA ABC" in lines[0].description
    assert lines[0].amount == Decimal("1200.00")


def test_parse_statement_generic_csv_bytes():
    content = b"data,descricao,valor\n2026-02-01,Teste,-10.00\n"
    result = parse_statement_file(content, "banco.csv")
    assert len(result.lines) == 1


def test_categorization_rule(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "t.db")
    init_database()
    cat = create_category("Delivery", TransactionType.EXPENSE, "🛵")
    create_rule("IFOOD", cat.id, "contains")
    assert suggest_category("Pedido IFOOD 123") == cat.id
    assert suggest_category("Supermercado") is None


def test_auto_cat_marker_preserves_user_notes():
    marked = append_auto_cat_marker("Nota do usuário")
    assert AUTO_CAT_MARKER in marked
    assert "Nota do usuário" in marked
    assert strip_system_notes(marked) == "Nota do usuário"


def test_manual_installment_plan(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "t.db")
    init_database()


    profile = create_profile("Parcelas")
    cat = create_category("Cartão", TransactionType.EXPENSE, "💳")
    count = create_installment_plan(
        profile_id=profile.id,
        category_id=cat.id,
        description="Notebook",
        total_amount=Decimal("1200"),
        installments=12,
        start_date=date(2026, 6, 10),
    )
    assert count == 12
    txs = get_transactions(profile_id=profile.id)
    assert len(txs) == 12
    assert txs[0].is_installment
    assert txs[0].installment_total == 12


def test_budget_alert(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "t.db")
    init_database()
    profile = create_profile("Test")
    cat = create_category("Food", TransactionType.EXPENSE, "🍔")
    set_budget(profile.id, cat.id, 2026, 6, 100.0)

    msg = check_budget_impact(
        profile.id, cat.id, Decimal("85"), date(2026, 6, 15), TransactionType.EXPENSE
    )
    assert msg is not None
    assert "85%" in msg or "80%" in msg or "Atenção" in msg

    over = check_budget_impact(
        profile.id, cat.id, Decimal("110"), date(2026, 6, 15), TransactionType.EXPENSE
    )
    assert over is not None
    assert "excedido" in over.lower()