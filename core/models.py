"""
OrcFin - Core Data Models
Pydantic models for type safety and validation across the application.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator

from core.domain.enums import ProfileType, TransactionType


class Profile(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    color: str = "#14B8A6"  # Default teal accent
    profile_type: ProfileType = ProfileType.PERSONAL
    created_at: Optional[datetime] = None
    is_active: bool = True


class MeiConfig(BaseModel):
    profile_id: int
    razao_social: str
    cnpj: str
    activity_type: Literal["comercio", "servico", "industria", "comercio_servico"] = "servico"
    custom_das_amount: Optional[float] = None
    annual_limit: float = 81000.0
    das_day: int = 20


class MeiClient(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str
    document: Optional[str] = None
    notes: Optional[str] = None


class MeiInvoice(BaseModel):
    id: Optional[int] = None
    profile_id: int
    invoice_number: str
    client_id: Optional[int] = None
    tomador_name: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    issue_date: date
    due_date: Optional[date] = None
    paid_at: Optional[date] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class Asset(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str = Field(..., min_length=1, max_length=120)
    asset_type: Literal["cash", "investment", "property", "vehicle", "other"] = "other"
    current_value: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class Liability(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str = Field(..., min_length=1, max_length=120)
    liability_type: Literal["loan", "credit_card", "mortgage", "other"] = "other"
    current_balance: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class InvestmentHolding(BaseModel):
    id: Optional[int] = None
    profile_id: int
    asset_class: Literal["stock", "fii", "fund", "etf", "crypto", "other"] = "stock"
    symbol: Optional[str] = None
    cnpj: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal = Field(..., ge=0)
    avg_cost: Decimal = Field(default=Decimal("0"), ge=0)
    applied_at: Optional[date] = None
    broker: Optional[str] = None
    notes: Optional[str] = None


class CreditCard(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str = Field(..., min_length=1, max_length=120)
    bank: str = Field(..., min_length=1, max_length=80)
    network: str = Field(default="Mastercard", max_length=40)
    last_four: Optional[str] = Field(default=None, max_length=4)
    closing_day: Optional[int] = Field(default=None, ge=1, le=31)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    color: str = "#8B5CF6"
    is_active: bool = True


class Category(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    type: TransactionType
    icon: Optional[str] = None  # Emoji or material icon name
    is_mei_deductible: bool = False
    created_at: Optional[datetime] = None


class Transaction(BaseModel):
    id: Optional[int] = None
    profile_id: int
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0)  # Always positive, sign determined by type
    category_id: int
    type: TransactionType
    is_recurring: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    is_installment: bool = False
    installment_group_id: Optional[str] = None
    installment_number: Optional[int] = None
    installment_total: Optional[int] = None
    mei_client_id: Optional[int] = None
    credit_card_id: Optional[int] = None
    import_batch_id: Optional[int] = None
    import_confidence: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class MonthlySummary(BaseModel):
    """Aggregated view for a specific month."""
    year: int
    month: int
    profile_id: Optional[int] = None  # None = consolidated
    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")
    net_savings: Decimal = Decimal("0")
    savings_rate: float = 0.0  # Percentage 0-100
    transaction_count: int = 0


class AIInsight(BaseModel):
    """Structure for AI generated insights."""
    provider: str
    model: str
    summary: str
    predictions: list[str]
    cost_reduction_tips: list[str]
    general_advice: str
    generated_at: datetime = Field(default_factory=datetime.now)


class AppSettings(BaseModel):
    """Local application settings stored in JSON."""
    theme_mode: Literal["dark", "light"] = "dark"
    currency: str = "BRL"
    default_profile_id: Optional[int] = None
    ai_provider: Optional[str] = None
    ai_provider_keys: dict[str, str] = Field(default_factory=dict)
    ai_provider_models: dict[str, str] = Field(default_factory=dict)
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None