"""LGPD: import stays local; AI context excludes PII."""

from datetime import date
from decimal import Decimal

import pytest

from core.engine.reporting import generate_ai_context
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.db.schema import init_database
from core.services.import_service import prepare_import
from core.models import Transaction, TransactionType
from core.privacy import assert_no_pii_in_ai_payload


def test_generate_ai_context_omits_profile_name(project_tmp_path, monkeypatch):
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "privacy.db")
    init_database()
    profile = create_profile("Pamela Silva")
    cat = create_category("Alimentação", TransactionType.EXPENSE)
    create_transaction(
        Transaction(
            profile_id=profile.id,
            date=date.today(),
            description="UBER TRIP SAO PAULO",
            amount=Decimal("45.90"),
            category_id=cat.id,
            type=TransactionType.EXPENSE,
            notes="import:Nubank_2026-06-10.pdf",
        )
    )

    context = generate_ai_context(profile_id=profile.id, consolidated=False)

    assert "Pamela" not in context
    assert "UBER" not in context
    assert "import:" not in context
    assert "identidade omitida" in context
    assert_no_pii_in_ai_payload(context)


def test_prepare_import_does_not_call_ai(monkeypatch, project_tmp_path):
    """Import parsers must never invoke external AI."""
    monkeypatch.setattr("core.db.connection.DB_PATH", project_tmp_path / "import.db")
    init_database()
    profile = create_profile("Import User")

    def _fail_ai(*_args, **_kwargs):
        raise AssertionError("AI must not be called during import")

    monkeypatch.setattr("core.ai_gateway.request_financial_insights", _fail_ai)

    csv_content = (
        "date,description,amount\n"
        "2026-06-01,MERCADO LOCAL,-120.50\n"
    ).encode("utf-8")

    result = prepare_import(csv_content, "extrato.csv", profile.id)
    assert result.lines