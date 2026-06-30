"""MEI operations — profile setup and DAS confirmation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Tuple

import core.db.repositories.mei as mei_repo
from core.db.repositories.transactions import (
    create_transaction,
    has_transaction_in_category_for_month,
)
from core.domain.entities.mei_profile import MeiProfile
from core.models import MeiConfig, Profile, Transaction, TransactionType


def create_mei_profile(
    name: str,
    razao_social: str,
    cnpj: str,
    activity_type: str = "servico",
    color: str = "#F59E0B",
    annual_limit: float = 81000.0,
) -> Tuple[Profile, MeiConfig]:
    return mei_repo.insert_mei_profile(
        name=name,
        razao_social=razao_social,
        cnpj=cnpj,
        activity_type=activity_type,
        color=color,
        annual_limit=annual_limit,
    )


def das_payment_exists(profile_id: int, year: int, month: int) -> bool:
    cat_id = mei_repo.get_das_category_id()
    if not cat_id:
        return False
    return has_transaction_in_category_for_month(profile_id, cat_id, year, month)


def confirm_das_payment(
    profile_id: int,
    payment_date: date,
    amount: Decimal,
) -> Optional[int]:
    """Record DAS payment as expense transaction. Returns None if already paid."""
    cat_id = mei_repo.get_das_category_id()
    if not cat_id:
        return None
    if das_payment_exists(profile_id, payment_date.year, payment_date.month):
        return None

    config = mei_repo.get_mei_config(profile_id)
    entity = MeiProfile(config) if config else None
    description = (
        entity.das_payment_description(payment_date)
        if entity
        else f"DAS MEI — {payment_date.month:02d}/{payment_date.year}"
    )
    created = create_transaction(
        Transaction(
            profile_id=profile_id,
            date=payment_date,
            description=description,
            amount=amount,
            category_id=cat_id,
            type=TransactionType.EXPENSE,
            notes="Pagamento confirmado pelo usuário",
        )
    )
    return created.id