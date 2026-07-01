from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from core.models import TransactionType


@dataclass
class ParsedStatementLine:
    date: date
    description: str
    amount: Decimal
    tx_type: TransactionType
    suggested_category_id: Optional[int] = None
    selected: bool = True
    is_duplicate: bool = False
    confidence: str = "medium"
    installment_number: Optional[int] = None
    installment_total: Optional[int] = None
    card_last_four: Optional[str] = None


@dataclass
class ParseResult:
    institution: str
    filename: str
    lines: list[ParsedStatementLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bank: Optional[str] = None
    card_network: Optional[str] = None
    card_last_four: Optional[str] = None
    statement_due_date: Optional[date] = None
    statement_total: Optional[Decimal] = None
    period_label: Optional[str] = None
    source_type: str = "bank_statement"
    credit_card_id: Optional[int] = None
    file_hash: Optional[str] = None
    parser_id: Optional[str] = None