"""Credit card helpers for import workflow."""

from __future__ import annotations

from typing import Optional

import core.db.repositories.credit_cards as card_repo
from core.models import CreditCard


def get_or_create_credit_card_from_import(
    profile_id: int,
    *,
    bank: str,
    network: str,
    last_four: Optional[str] = None,
    due_day: Optional[int] = None,
) -> CreditCard:
    existing = card_repo.find_credit_card(profile_id, bank, last_four, network)
    if existing:
        return existing

    label = f"{bank} {network}"
    if last_four:
        label += f" •••• {last_four}"
    return card_repo.create_credit_card(
        CreditCard(
            profile_id=profile_id,
            name=label,
            bank=bank,
            network=network,
            last_four=last_four,
            due_day=due_day,
        )
    )