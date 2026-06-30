"""Import workflow: parse → suggest categories → preview → commit.

All steps run locally on the device. Invoice bytes, holder names, card data
and merchant lines are never sent to external AI or cloud APIs (LGPD).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from core.engine.categorization import suggest_category
from core.db.repositories.categories import get_categories_for_profile
from core.db.repositories.transactions import (
    create_transaction,
    existing_import_keys,
    import_match_key,
    log_import,
)
from core.import_parsers import ParseResult, parse_statement_file
from core.import_parsers.models import ParsedStatementLine
from core.models import Transaction, TransactionType
from core.services.credit_card_service import get_or_create_credit_card_from_import


def _default_category_id(tx_type: TransactionType, profile_id: int) -> int:
    categories = get_categories_for_profile(profile_id)
    matching = [c for c in categories if c.type == tx_type]
    return matching[0].id if matching else categories[0].id


def _attach_credit_card(result: ParseResult, profile_id: int) -> None:
    if result.source_type != "credit_card_invoice" or not result.bank:
        return
    due_day = result.statement_due_date.day if result.statement_due_date else None
    card = get_or_create_credit_card_from_import(
        profile_id,
        bank=result.bank,
        network=result.card_network or "Mastercard",
        last_four=result.card_last_four,
        due_day=due_day,
    )
    result.credit_card_id = card.id


def prepare_import(
    content: bytes,
    filename: str,
    profile_id: int,
) -> ParseResult:
    result = parse_statement_file(content, filename)
    _attach_credit_card(result, profile_id)
    for line in result.lines:
        suggested = suggest_category(line.description, profile_id)
        visible_ids = {c.id for c in get_categories_for_profile(profile_id)}
        if suggested and suggested not in visible_ids:
            suggested = None
        line.suggested_category_id = suggested or _default_category_id(line.tx_type, profile_id)
    dupes = _flag_import_duplicates(result.lines, profile_id)
    if dupes:
        result.warnings.append(
            f"{dupes} lançamento(s) já existem (data + valor + descrição) — desmarcados automaticamente"
        )
    return result


def _flag_import_duplicates(lines: list[ParsedStatementLine], profile_id: int) -> int:
    if not lines:
        return 0
    dates = [line.date for line in lines]
    existing = existing_import_keys(profile_id, min(dates), max(dates))
    seen: set[tuple[str, str, str]] = set()
    dupes = 0
    for line in lines:
        key = import_match_key(line.date, line.amount, line.description)
        if key in existing or key in seen:
            line.is_duplicate = True
            line.selected = False
            dupes += 1
        else:
            seen.add(key)
    return dupes


def commit_import(
    lines: list[ParsedStatementLine],
    profile_id: int,
    filename: str,
    credit_card_id: int | None = None,
) -> int:
    count = 0
    for line in lines:
        if not line.selected:
            continue
        installment_meta = None
        if line.installment_number and line.installment_total:
            installment_meta = {
                "is_installment": True,
                "installment_number": line.installment_number,
                "installment_total": line.installment_total,
            }
        create_transaction(
            Transaction(
                profile_id=profile_id,
                date=line.date,
                description=line.description,
                amount=line.amount,
                category_id=line.suggested_category_id or _default_category_id(line.tx_type, profile_id),
                type=line.tx_type,
                notes=f"import:{filename}",
                credit_card_id=credit_card_id,
                is_installment=bool(installment_meta),
                installment_number=line.installment_number,
                installment_total=line.installment_total,
            ),
            installment_meta=installment_meta,
        )
        count += 1
    if count:
        log_import(filename, count, profile_id)
    return count


def create_installment_plan(
    profile_id: int,
    category_id: int,
    description: str,
    total_amount: Decimal,
    installments: int,
    start_date: date,
    tx_type: TransactionType = TransactionType.EXPENSE,
) -> int:
    """Create N monthly installment transactions."""
    if installments < 2:
        raise ValueError("Parcelamento requer pelo menos 2 parcelas")

    group_id = str(uuid.uuid4())
    per = (total_amount / installments).quantize(Decimal("0.01"))
    created = 0
    year, month = start_date.year, start_date.month

    for i in range(1, installments + 1):
        m = month + (i - 1)
        y = year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        tx_date = date(y, m, min(start_date.day, 28))

        create_transaction(
            Transaction(
                profile_id=profile_id,
                date=tx_date,
                description=f"{description} ({i}/{installments})",
                amount=per,
                category_id=category_id,
                type=tx_type,
                notes=f"installment:{group_id}",
            ),
            installment_meta={
                "is_installment": True,
                "installment_group_id": group_id,
                "installment_number": i,
                "installment_total": installments,
            },
        )
        created += 1
    return created