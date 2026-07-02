"""PDF generation smoke tests."""

from datetime import date
from decimal import Decimal

from core.db.repositories.mei import create_mei_client, create_mei_invoice, get_mei_invoices
from core.demo_data import seed_demo_mei_data
from core.models import MeiClient, MeiInvoice
from core.pdf_generator import generate_mei_service_receipt_pdf
from core.services.mei_service import create_mei_profile


def test_mei_service_receipt_pdf(fresh_db, project_tmp_path):
    count, profile_id = seed_demo_mei_data(operational_profile="on_demand")
    assert count > 0
    assert profile_id is not None

    invoices = get_mei_invoices(profile_id)
    assert invoices
    out = project_tmp_path / "recibo.pdf"
    path = generate_mei_service_receipt_pdf(profile_id, invoices[0]["id"], out)
    assert path.exists()
    assert path.stat().st_size > 500


def test_mei_receipt_pdf_minimal(fresh_db, project_tmp_path):
    profile, _ = create_mei_profile(
        name="MEI PDF",
        razao_social="Teste MEI",
        cnpj="11.111.111/0001-11",
    )
    client = create_mei_client(MeiClient(profile_id=profile.id, name="Cliente PDF"))
    invoice = create_mei_invoice(
        MeiInvoice(
            profile_id=profile.id,
            invoice_number="NF-TEST-001",
            client_id=client.id,
            tomador_name=client.name,
            amount=Decimal("500"),
            issue_date=date.today(),
        )
    )
    out = project_tmp_path / "recibo_min.pdf"
    path = generate_mei_service_receipt_pdf(profile.id, invoice.id, out)
    assert path.exists()