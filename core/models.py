"""
OrcFin - Core Data Models
Pydantic models for type safety and validation across the application.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator

from core.domain.enums import ProfileType, TransactionType

__all__ = [
    "Profile",
    "MeiConfig",
    "MeiClient",
    "MeiInvoice",
    "MeiSupplier",
    "MeiOrder",
    "MeiOrderOutsource",
    "MeiSubscription",
    "MeiSubscriptionCharge",
    "MeiProduct",
    "MeiStockMovement",
    "Asset",
    "Liability",
    "InvestmentHolding",
    "CreditCard",
    "Category",
    "Transaction",
    "MonthlySummary",
    "AIInsight",
    "AppSettings",
    "ProfileType",
    "TransactionType",
]


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
    operational_profile: Literal[
        "sales", "on_demand", "by_order", "recurring", "mixed"
    ] = "on_demand"
    cnae: Optional[str] = None
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


class MeiSupplier(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str
    document: Optional[str] = None
    notes: Optional[str] = None


class MeiOrder(BaseModel):
    id: Optional[int] = None
    profile_id: int
    client_id: Optional[int] = None
    reference: str
    revenue_amount: Decimal = Field(..., ge=0)
    order_date: date
    status: Literal["open", "done"] = "open"
    notes: Optional[str] = None


class MeiOrderOutsource(BaseModel):
    id: Optional[int] = None
    order_id: int
    supplier_id: int
    amount: Decimal = Field(..., gt=0)
    sent_date: Optional[date] = None
    paid_at: Optional[date] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class MeiSubscription(BaseModel):
    id: Optional[int] = None
    profile_id: int
    client_id: Optional[int] = None
    name: str
    monthly_amount: Decimal = Field(..., gt=0)
    due_day: int = Field(default=10, ge=1, le=28)
    start_date: date
    end_date: Optional[date] = None
    status: Literal["active", "paused", "cancelled"] = "active"
    notes: Optional[str] = None


class MeiSubscriptionCharge(BaseModel):
    id: Optional[int] = None
    subscription_id: int
    year: int
    month: int
    due_date: date
    amount: Decimal = Field(..., gt=0)
    paid_at: Optional[date] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class MeiProduct(BaseModel):
    id: Optional[int] = None
    profile_id: int
    name: str
    sku: Optional[str] = None
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    stock_qty: Decimal = Field(default=Decimal("0"), ge=0)
    low_stock_threshold: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None


class MeiStockMovement(BaseModel):
    id: Optional[int] = None
    product_id: int
    movement_type: Literal["in", "out", "adjust"]
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    movement_date: date
    notes: Optional[str] = None
    transaction_id: Optional[int] = None


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