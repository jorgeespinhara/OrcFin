"""Dashboard decision cards."""

from datetime import date
from decimal import Decimal

from core.db.repositories.categories import get_categories_for_profile
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import create_transaction
from core.engine.decisions import get_decision_cards
from core.models import Transaction, TransactionType


def test_decision_cards_include_spendable(fresh_db):
    profile_id = get_all_profiles()[0].id
    income = next(c for c in get_categories_for_profile(profile_id) if c.type == TransactionType.INCOME)
    today = date.today()
    create_transaction(
        Transaction(
            profile_id=profile_id,
            date=today,
            description="Salário",
            amount=Decimal("3000"),
            category_id=income.id,
            type=TransactionType.INCOME,
        )
    )
    cards = get_decision_cards(profile_id=profile_id, year=today.year, month=today.month)
    assert cards
    assert any(c["id"] == "spendable" for c in cards)