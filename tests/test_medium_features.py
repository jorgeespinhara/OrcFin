"""Medium-term features: due dates, transfers, split, MEI pack."""

from datetime import date
from decimal import Decimal

from core.db.repositories.categories import create_category
from core.db.repositories.profiles import create_profile
from core.db.repositories.transactions import (
    TRANSFER_NOTE,
    create_internal_transfer,
    create_transaction,
    get_transactions,
    split_transaction,
)
from core.db.queries import get_consolidated_summary
from core.engine.due_dates import get_upcoming_due_dates
from core.models import CreditCard, Transaction, TransactionType


def test_split_transaction(fresh_db):
    p = create_profile("SplitTest")
    c1 = create_category("Cat1", TransactionType.EXPENSE)
    c2 = create_category("Cat2", TransactionType.EXPENSE)
    tx = create_transaction(
        Transaction(
            profile_id=p.id,
            date=date(2026, 6, 1),
            description="Compra",
            amount=Decimal("100"),
            category_id=c1.id,
            type=TransactionType.EXPENSE,
        )
    )
    split_transaction(tx.id, [(c1.id, Decimal("60")), (c2.id, Decimal("40"))])
    rows = get_transactions(profile_id=p.id)
    assert len(rows) == 2
    assert sum(r.amount for r in rows) == Decimal("100")


def test_internal_transfer_excluded_from_consolidated(fresh_db):
    from core.db.repositories.categories import get_all_categories

    a, b = create_profile("XferA"), create_profile("XferB")
    exp = next(c for c in get_all_categories() if c.type == TransactionType.EXPENSE)
    inc = next(c for c in get_all_categories() if c.type == TransactionType.INCOME)
    create_internal_transfer(a.id, b.id, Decimal("500"), "Entre contas", date(2026, 6, 10), exp.id, inc.id)
    s = get_consolidated_summary(2026, 6)
    assert s["total_income"] == Decimal("0")
    assert s["total_expense"] == Decimal("0")
    assert get_transactions(profile_id=a.id)[0].notes == TRANSFER_NOTE


def test_due_dates_includes_card(fresh_db):
    from core.db.repositories.credit_cards import create_credit_card

    p = create_profile("DueTest")
    create_credit_card(CreditCard(profile_id=p.id, name="Nubank", bank="Nubank", network="Visa", due_day=15))
    items = get_upcoming_due_dates(p.id, False)
    assert any(i["kind"] == "card" for i in items)