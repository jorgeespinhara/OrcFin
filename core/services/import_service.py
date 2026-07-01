"""Import workflow: parse → suggest categories → preview → commit.

All steps run locally on the device. Invoice bytes, holder names, card data
and merchant lines are never sent to external AI or cloud APIs (LGPD).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from core.db.repositories.import_batches import (
    create_import_batch,
    update_batch_imported_count,
)
from core.change_log import log_change
from core.engine.categorization import suggest_category_with_confidence
from core.db.repositories.categories import get_categories_for_profile
from core.db.repositories.transactions import (
    create_transaction,
    existing_import_keys,
    import_match_key,
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
    *,
    column_map: dict[str, str] | None = None,
) -> ParseResult:
    result = parse_statement_file(content, filename, column_map=column_map)
    result.file_hash = hashlib.sha256(content).hexdigest()
    _attach_credit_card(result, profile_id)
    for line in result.lines:
        suggested, confidence = suggest_category_with_confidence(line.description, profile_id)
        visible_ids = {c.id for c in get_categories_for_profile(profile_id)}
        if suggested and suggested not in visible_ids:
            suggested = None
        line.suggested_category_id = suggested or _default_category_id(line.tx_type, profile_id)
        line.confidence = confidence
    dupes = _flag_import_duplicates(result.lines, profile_id)
    for line in result.lines:
        if line.is_duplicate:
            line.confidence = "review"
    if dupes:
        result.warnings.append(
            f"{dupes} lançamento(s) já existem (data + valor + descrição) e foram desmarcados automaticamente"
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
    result: ParseResult,
    profile_id: int,
    *,
    lines: list[ParsedStatementLine] | None = None,
    credit_card_id: int | None = None,
) -> tuple[int, int | None]:
    """Import selected lines and register a reversible batch."""
    source_lines = lines if lines is not None else result.lines
    selected = [line for line in source_lines if line.selected]
    rows_total = len(result.lines)
    rows_skipped = rows_total - len(selected)
    card_id = credit_card_id or result.credit_card_id
    if not selected:
        return 0, None

    batch_id = create_import_batch(
        profile_id=profile_id,
        filename=result.filename,
        source_type=result.source_type,
        source_bank=result.bank or result.institution,
        parser_name=result.institution,
        file_hash=result.file_hash,
        rows_total=rows_total,
        rows_imported=0,
        rows_skipped=rows_skipped,
        notes=result.period_label,
    )

    count = 0
    for line in selected:
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
                notes=f"import:{result.filename}",
                credit_card_id=card_id,
                is_installment=bool(installment_meta),
                installment_number=line.installment_number,
                installment_total=line.installment_total,
                import_batch_id=batch_id,
                import_confidence=line.confidence,
            ),
            installment_meta=installment_meta,
        )
        count += 1

    update_batch_imported_count(batch_id, count)
    log_change(
        "import",
        "commit",
        f"{count} lançamentos de {result.filename}",
        entity_id=batch_id,
    )
    return count, batch_id


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