"""Tests for MEI module."""

from datetime import date
from decimal import Decimal

import pytest

from core.db.repositories.categories import get_all_categories
from core.db.repositories.mei import (
    create_mei_client,
    create_mei_invoice,
    get_mei_config,
    get_mei_deductible_category_ids,
)
from core.db.repositories.transactions import create_transaction
from core.db.schema import init_database
from core.domain.entities.mei_profile import DAS_AMOUNTS, MeiProfile
from core.mei import (
    get_mei_dashboard_data,
    get_obligations_checklist,
    get_revenue_by_client,
    get_revenue_limit_status,
    get_simplified_report,
    get_ytd_revenue_evolution,
)
from core.models import Transaction, TransactionType, MeiClient, MeiInvoice
from core.services.mei_service import confirm_das_payment, create_mei_profile, das_payment_exists


@pytest.fixture(autouse=True)
def _db(project_tmp_path, monkeypatch):
    db_path = project_tmp_path / "test.db"
    monkeypatch.setattr("core.db.connection.DB_PATH", db_path)
    init_database()
    yield


def _profile(activity_type: str, custom_das: float | None = None) -> MeiProfile:
    from core.models import MeiConfig

    return MeiProfile(
        MeiConfig(
            profile_id=0,
            razao_social="",
            cnpj="",
            activity_type=activity_type,  # type: ignore[arg-type]
            custom_das_amount=custom_das,
        )
    )


def test_das_amounts_by_activity():
    assert _profile("comercio").das_amount() == DAS_AMOUNTS["comercio"]
    assert _profile("servico").das_amount() == DAS_AMOUNTS["servico"]
    assert _profile("servico", custom_das=99.0).das_amount() == Decimal("99")


def test_create_mei_profile_and_config():
    profile, config = create_mei_profile(
        name="MEI Test",
        razao_social="João MEI LTDA",
        cnpj="12.345.678/0001-99",
        activity_type="servico",
    )
    assert profile.id is not None
    loaded = get_mei_config(profile.id)
    assert loaded is not None
    assert loaded.razao_social == "João MEI LTDA"
    assert loaded.cnpj == "12.345.678/0001-99"


def test_revenue_limit_and_projection():
    profile, _ = create_mei_profile("MEI", "Empresa", "11.111.111/0001-11")
    income_cat = next(c for c in get_all_categories() if c.name == "Receita MEI")

    for month in range(1, 4):
        create_transaction(
            Transaction(
                profile_id=profile.id,
                category_id=income_cat.id,
                description=f"Serviço m{month}",
                amount=Decimal("2000"),
                date=date(2026, month, 10),
                type=TransactionType.INCOME,
            )
        )

    status = get_revenue_limit_status(profile.id, Decimal("81000"))
    assert status["ytd_revenue"] == Decimal("6000")
    assert status["percentage"] == pytest.approx(7.4, abs=0.1)
    config = get_mei_config(profile.id)
    assert MeiProfile(config).project_limit_reach_date(status["ytd_revenue"], date(2026, 3, 15)) is not None


def test_simplified_report_deductible_split():
    profile, _ = create_mei_profile("MEI Dedutível", "Empresa", "22.222.222/0001-22")
    cats = {c.name: c.id for c in get_all_categories()}
    deductible_ids = get_mei_deductible_category_ids()
    assert len(deductible_ids) >= 1

    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=cats["Receita MEI"],
            description="Projeto A",
            amount=Decimal("5000"),
            date=date(2026, 6, 1),
            type=TransactionType.INCOME,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=cats["Materiais e Insumos"],
            description="Insumos",
            amount=Decimal("500"),
            date=date(2026, 6, 2),
            type=TransactionType.EXPENSE,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=cats["DAS / Impostos MEI"],
            description="DAS",
            amount=Decimal("75.90"),
            date=date(2026, 6, 20),
            type=TransactionType.EXPENSE,
        )
    )

    report = get_simplified_report(profile.id, deductible_category_ids=deductible_ids)
    assert report["gross_revenue"] == Decimal("5000")
    assert report["deductible_expenses"] == Decimal("500")
    assert report["non_deductible_expenses"] == Decimal("75.90")
    assert report["simplified_result"] == Decimal("4500")


def test_das_payment_confirmation():
    profile, config = create_mei_profile("MEI DAS", "Empresa", "33.333.333/0001-33")
    amount = MeiProfile(config).das_amount()
    tx_id = confirm_das_payment(profile.id, date(2026, 6, 20), amount)
    assert tx_id is not None
    assert das_payment_exists(profile.id, 2026, 6)
    assert confirm_das_payment(profile.id, date(2026, 6, 21), amount) is None


def test_mei_invoice_and_client():
    profile, _ = create_mei_profile("MEI NF", "Empresa", "44.444.444/0001-44")
    client = create_mei_client(MeiClient(profile_id=profile.id, name="Cliente X"))
    inv = create_mei_invoice(
        MeiInvoice(
            profile_id=profile.id,
            invoice_number="NF-001",
            client_id=client.id,
            tomador_name="Cliente X",
            amount=Decimal("1500"),
            issue_date=date(2026, 5, 1),
        )
    )
    assert inv.id is not None


def test_das_due_info():
    profile, config = create_mei_profile("MEI Due", "Empresa", "66.666.666/0001-66")
    info = MeiProfile(config).das_due_info(date(2026, 6, 15))
    assert info["due_date"].day == 20
    assert info["days_left"] == 5


def test_revenue_by_client():
    profile, _ = create_mei_profile("MEI Clientes", "Empresa", "55.555.555/0001-55")
    income_cat = next(c for c in get_all_categories() if c.name == "Receita MEI")
    client_a = create_mei_client(MeiClient(profile_id=profile.id, name="Cliente A"))
    client_b = create_mei_client(MeiClient(profile_id=profile.id, name="Cliente B"))

    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Projeto A",
            amount=Decimal("1000"),
            date=date(2026, 4, 1),
            type=TransactionType.INCOME,
            mei_client_id=client_a.id,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Projeto B",
            amount=Decimal("2500"),
            date=date(2026, 5, 1),
            type=TransactionType.INCOME,
            mei_client_id=client_b.id,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Avulso",
            amount=Decimal("300"),
            date=date(2026, 5, 15),
            type=TransactionType.INCOME,
        )
    )

    by_client = get_revenue_by_client(profile.id, 2026)
    totals = {row["name"]: row["total"] for row in by_client}
    assert totals["Cliente B"] == Decimal("2500")
    assert totals["Cliente A"] == Decimal("1000")
    assert totals["Sem cliente vinculado"] == Decimal("300")


def test_mei_dashboard_data():
    today = date.today()
    profile, _ = create_mei_profile("MEI Dashboard", "Empresa", "66.666.666/0001-66")
    income_cat = next(c for c in get_all_categories() if c.name == "Receita MEI")
    expense_cat = next(c for c in get_all_categories() if c.name == "Materiais e Insumos")

    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Serviço",
            amount=Decimal("800"),
            date=today,
            type=TransactionType.INCOME,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=expense_cat.id,
            description="Material",
            amount=Decimal("200"),
            date=today,
            type=TransactionType.EXPENSE,
        )
    )

    dash = get_mei_dashboard_data(profile.id)
    assert dash["month_income"] == Decimal("800")
    assert dash["month_expense"] == Decimal("200")
    assert dash["ytd_income"] >= Decimal("800")
    assert "limit_status" in dash
    assert len(dash["ytd_evolution"]) >= 1


def test_obligations_checklist():
    today = date.today()
    profile, config = create_mei_profile("MEI Obrigações", "Empresa", "77.777.777/0001-77")
    income_cat = next(c for c in get_all_categories() if c.name == "Receita MEI")

    create_mei_invoice(
        MeiInvoice(
            profile_id=profile.id,
            invoice_number="NF-100",
            tomador_name="Tomador",
            amount=Decimal("500"),
            issue_date=today,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Serviço",
            amount=Decimal("500"),
            date=today,
            type=TransactionType.INCOME,
        )
    )
    confirm_das_payment(profile.id, today, MeiProfile(config).das_amount())

    checklist = get_obligations_checklist(profile.id)
    by_id = {item["id"]: item for item in checklist}
    assert by_id["das"]["done"] is True
    assert by_id["nf_month"]["done"] is True
    assert by_id["reconcile"]["done"] is True
    assert by_id["limit"]["done"] is True


def test_ytd_revenue_evolution():
    profile, _ = create_mei_profile("MEI Evolução", "Empresa", "88.888.888/0001-88")
    income_cat = next(c for c in get_all_categories() if c.name == "Receita MEI")

    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Jan",
            amount=Decimal("100"),
            date=date(2026, 1, 10),
            type=TransactionType.INCOME,
        )
    )
    create_transaction(
        Transaction(
            profile_id=profile.id,
            category_id=income_cat.id,
            description="Fev",
            amount=Decimal("200"),
            date=date(2026, 2, 10),
            type=TransactionType.INCOME,
        )
    )

    evolution = get_ytd_revenue_evolution(profile.id, 2026)
    assert len(evolution) >= 2
    assert evolution[0]["cumulative"] == Decimal("100")
    assert evolution[1]["cumulative"] == Decimal("300")