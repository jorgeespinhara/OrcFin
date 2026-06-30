"""Phase 3: bank parsers, NF-e XML, planning, open export, calendar."""

from datetime import date
from decimal import Decimal

from core.data_export import export_open_data_json, export_transactions_csv
from core.engine.local_insights import get_local_finance_insights
from core.engine.spendable import get_spendable_amount
from core.import_parsers import parse_statement_file
from core.import_parsers.detect import detect_csv_institution
from core.mei_calendar import export_das_ics
from core.mei_nfe_xml import import_nfe_xml, parse_nfe_xml
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.models import Transaction, TransactionType
from core.services.mei_service import create_mei_profile


_NFE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe>
      <ide><nNF>98765</nNF><dhEmi>2026-06-15T10:00:00-03:00</dhEmi></ide>
      <dest><xNome>Cliente XML Teste</xNome></dest>
      <total><ICMSTot><vNF>2500.50</vNF></ICMSTot></total>
    </infNFe>
  </NFe>
</nfeProc>"""


def test_detect_inter_and_c6_csv():
    inter = "Data,Descrição,Valor\n2026-06-01,Banco Inter PIX,100.00\n"
    assert detect_csv_institution(inter) == "inter"
    c6 = "Data,Descrição,Valor\n2026-06-02,C6 Bank compra,-45.90\n"
    head = "Extrato C6 Bank\n" + c6
    assert detect_csv_institution(head) == "c6"


def test_parse_inter_csv(fresh_db):
    csv = (
        b"Extrato Banco Inter\n"
        b"Data,Descricao,Valor\n"
        b"2026-06-10,PIX recebido,500.00\n"
        b"2026-06-11,Mercado,-120.50\n"
    )
    result = parse_statement_file(csv, "inter.csv")
    assert result.institution == "Banco Inter"
    assert len(result.lines) == 2
    assert result.lines[0].tx_type == TransactionType.INCOME


def test_parse_bradesco_csv(fresh_db):
    csv = (
        "Data;Histórico;Valor\n"
        "10/06/2026;Supermercado;-150,00\n"
        "11/06/2026;Salário;3000,00\n"
    )
    result = parse_statement_file(csv.encode(), "bradesco.csv")
    assert result.institution == "Bradesco"
    assert len(result.lines) == 2
    assert result.lines[1].tx_type == TransactionType.INCOME


def test_parse_nfe_xml_fields():
    data = parse_nfe_xml(_NFE_XML)
    assert data["invoice_number"] == "98765"
    assert data["tomador_name"] == "Cliente XML Teste"
    assert data["amount"] == Decimal("2500.50")
    assert data["issue_date"] == date(2026, 6, 15)


def test_import_nfe_xml_creates_invoice(fresh_db):
    profile, _ = create_mei_profile("MEI XML", "Empresa", "11.111.111/0001-11")
    inv = import_nfe_xml(profile.id, _NFE_XML)
    assert inv.id
    assert inv.invoice_number == "98765"
    assert inv.amount == Decimal("2500.50")


def test_spendable_amount_non_negative(fresh_db):
    p = create_profile("Plan")
    inc = create_category("Sal", TransactionType.INCOME)
    exp = create_category("Gasto", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=inc.id,
            description="Salário",
            amount=Decimal("5000"),
            date=date(2026, 6, 5),
            type=TransactionType.INCOME,
        )
    )
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=exp.id,
            description="Aluguel",
            amount=Decimal("2000"),
            date=date(2026, 6, 8),
            type=TransactionType.EXPENSE,
        )
    )
    s = get_spendable_amount(profile_id=p.id, year=2026, month=6)
    assert s["income"] == Decimal("5000")
    assert s["spendable"] >= Decimal("0")


def test_local_insights_returns_list(fresh_db):
    p = create_profile("Insight")
    tips = get_local_finance_insights(profile_id=p.id, year=2026, month=6)
    assert isinstance(tips, list)
    assert tips


def test_open_data_export(fresh_db):
    p = create_profile("Export")
    cat = create_category("Mercado", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=cat.id,
            description="Teste export",
            amount=Decimal("42"),
            date=date(2026, 6, 1),
            type=TransactionType.EXPENSE,
        )
    )
    csv_path = export_transactions_csv(p.id)
    json_path = export_open_data_json(p.id)
    assert csv_path.exists()
    assert json_path.exists()
    assert "Teste export" in csv_path.read_text(encoding="utf-8")


def test_export_das_ics(fresh_db):
    profile, _ = create_mei_profile("MEI Cal", "Empresa", "22.222.222/0001-22")
    path = export_das_ics(profile.id, months_ahead=3)
    text = path.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in text
    assert "DAS MEI" in text