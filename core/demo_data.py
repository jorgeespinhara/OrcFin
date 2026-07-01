"""Sample transactions for onboarding demo mode."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.db.repositories.categories import get_all_categories
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import create_transaction
from core.models import Transaction, TransactionType


def seed_demo_transactions() -> int:
    profiles = get_all_profiles()
    if not profiles:
        return 0
    profile_id = profiles[0].id
    categories = {c.name: c for c in get_all_categories()}
    income = categories.get("Salário")
    food = categories.get("Alimentação (Mercado + Refeições)")
    transport = categories.get("Transporte (Combustível/Uber/Transporte Público)")
    if not income or not food or not transport:
        return 0

    today = date.today()
    samples = [
        ("Salário demo", Decimal("4500"), income.id, TransactionType.INCOME, 1),
        ("Supermercado demo", Decimal("320.50"), food.id, TransactionType.EXPENSE, 3),
        ("Combustível demo", Decimal("180"), transport.id, TransactionType.EXPENSE, 8),
        ("Freelance demo", Decimal("900"), income.id, TransactionType.INCOME, 12),
    ]
    created = 0
    for desc, amount, cat_id, tx_type, day in samples:
        try:
            create_transaction(
                Transaction(
                    profile_id=profile_id,
                    category_id=cat_id,
                    description=desc,
                    amount=amount,
                    date=date(today.year, today.month, min(day, 28)),
                    type=tx_type,
                    notes="demo:onboarding",
                )
            )
            created += 1
        except Exception:
            continue
    return created