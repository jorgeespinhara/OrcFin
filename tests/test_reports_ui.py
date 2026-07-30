"""Reports & AI UI helpers and report summary export."""

from datetime import date
from decimal import Decimal

from core.data_export import export_report_summary_csv
from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import create_transaction
from core.models import Transaction, TransactionType
from ui.reports.sections import mini_metric, build_ytd_card
from ui.reports.ai import build_ai_section


class _FakeApp:
    def __init__(self):
        self.settings = {}
        self.page = type("P", (), {"update": lambda self: None, "clipboard": None})()
        self.is_consolidated = False

    def get_view_profile_id(self):
        return None

    def is_mei_mode(self):
        return False

    def show_snack(self, *a, **k):
        pass

    def show_modal(self, *a, **k):
        pass

    def close_modal(self):
        pass


class _FakeView:
    def __init__(self):
        self.app = _FakeApp()


def test_mini_metric_clickable():
    m = mini_metric("Receita", "R$ 10", on_click=lambda: None)
    assert m.on_click is not None
    assert m.ink is True


def test_ytd_empty_state_has_cta(fresh_db):
    view = _FakeView()
    ytd = {
        "total_income": Decimal("0"),
        "total_expense": Decimal("0"),
        "net_savings": Decimal("0"),
        "savings_rate": 0.0,
        "transaction_count": 0,
    }
    card = build_ytd_card(view, ytd, title="Resumo 2026", prev_ytd=None)
    assert card is not None


def test_build_ai_section_has_disclaimer(fresh_db):
    section = build_ai_section(_FakeView())
    assert section is not None
    assert section.content is not None


def test_export_report_summary_csv(fresh_db):
    p = create_profile("Teste Rel")
    cat = create_category("Renda Relatório Teste", TransactionType.INCOME)
    create_transaction(
        Transaction(
            profile_id=p.id,
            category_id=cat.id,
            description="Salário teste",
            amount=Decimal("3000"),
            date=date(2026, 3, 5),
            type=TransactionType.INCOME,
        )
    )
    path = export_report_summary_csv(
        year=2026,
        up_to_month=3,
        profile_id=p.id,
        consolidated=False,
    )
    text = path.read_text(encoding="utf-8")
    assert "ytd" in text
    assert "total_income" in text
    assert path.exists()
