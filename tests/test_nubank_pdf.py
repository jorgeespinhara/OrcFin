from decimal import Decimal
from pathlib import Path

import pytest

from core.import_parsers.nubank_pdf import parse_nubank_pdf, is_nubank_invoice_pdf
from core.import_parsers.pdf_parser import _extract_pdf_text
from core.models import TransactionType

PDF_PATH = Path(__file__).resolve().parent.parent / "Nubank_2026-06-10.pdf"


@pytest.mark.skipif(not PDF_PATH.exists(), reason="Sample PDF not in workspace")
def test_nubank_sample_pdf_parse():
    content = PDF_PATH.read_bytes()
    text = _extract_pdf_text(content)
    assert is_nubank_invoice_pdf(text)

    result = parse_nubank_pdf(content, PDF_PATH.name)
    assert result.bank == "Nubank"
    assert result.card_network == "Mastercard"
    assert result.card_last_four == "0658"
    assert result.statement_total == Decimal("180.42")
    assert len(result.lines) >= 6

    expenses = [line for line in result.lines if line.tx_type == TransactionType.EXPENSE]
    payments = [line for line in result.lines if line.tx_type == TransactionType.INCOME]
    assert any("Cantina Amadori" in line.description for line in expenses)
    assert any("Pagamento" in line.description for line in payments)