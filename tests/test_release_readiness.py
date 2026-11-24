"""Tests for release-readiness features: Undo, batch category, diagnostics, update check, onboarding."""

from datetime import date
from decimal import Decimal

from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import (
    create_transaction,
    get_transaction,
    restore_transactions,
    soft_delete_transactions,
    update_transactions_category_batch,
)
from core.diagnostics import build_diagnostics_report, export_diagnostics, scrub_text
from core.domain.value_objects.money import currency_symbol
from core.models import Transaction, TransactionType
from core.update_check import check_for_updates, is_newer_version, parse_version
from ui.onboarding.view import _step_flow
from ui.transactions.data import parse_brl_amount


def test_soft_delete_restore_and_batch_category(fresh_db):
    p = create_profile("Teste")
    c1 = create_category("Cat A", TransactionType.EXPENSE)
    c2 = create_category("Cat B", TransactionType.EXPENSE)
    tx = create_transaction(
        Transaction(
            profile_id=p.id,
            date=date.today(),
            description="Mercado",
            amount=Decimal("42.50"),
            category_id=c1.id,
            type=TransactionType.EXPENSE,
        )
    )

    assert soft_delete_transactions([tx.id]) == 1
    assert get_transaction(tx.id) is None

    assert restore_transactions([tx.id]) == 1
    restored = get_transaction(tx.id)
    assert restored is not None
    assert restored.category_id == c1.id

    assert update_transactions_category_batch([tx.id], c2.id) == 1
    assert get_transaction(tx.id).category_id == c2.id


def test_currency_symbol_and_multi_currency_amount_parser():
    assert currency_symbol("BRL") == "R$"
    assert currency_symbol("USD") == "$"
    assert currency_symbol("EUR") == "€"
    assert parse_brl_amount("R$ 1.234,56") == Decimal("1234.56")
    assert parse_brl_amount("$ 99.50") == Decimal("99.50")
    assert parse_brl_amount("€ 15,20") == Decimal("15.20")


def test_diagnostics_scrubbing_and_export(project_tmp_path):
    raw = (
        "Error for alice@example.com CPF 123.456.789-01 "
        "path C:\\Users\\jorge\\secret.db amount R$ 1.500,00 token sk-1234567890abcdef"
    )
    cleaned = scrub_text(raw)
    assert "alice@example.com" not in cleaned
    assert "123.456.789-01" not in cleaned
    assert "jorge" not in cleaned
    assert "1.500,00" not in cleaned
    assert "sk-1234567890abcdef" not in cleaned

    report = build_diagnostics_report()
    assert "[Environment]" in report
    assert "[Safe Preferences]" in report

    out = export_diagnostics(dest_dir=project_tmp_path)
    assert out.exists()
    assert out.suffix == ".txt"


def test_update_check_versions_and_offline_guard(monkeypatch):
    assert parse_version("v1.0.0") == (1, 0, 0)
    assert is_newer_version("v1.1.0", "1.0.0") is True
    assert is_newer_version("v1.0.0", "1.0.0") is False

    monkeypatch.setattr("core.update_check.load_settings", lambda: {"strict_offline": True})
    res = check_for_updates()
    assert res["status"] == "offline"


def test_streamlined_onboarding_step_flow():
    assert _step_flow("personal", "BR") == ["welcome", "mode", "start"]
    assert _step_flow("mei", "BR") == ["welcome", "mode", "mei_profile", "start"]
    assert _step_flow("mei", "US") == ["welcome", "mode", "start"]
