"""Sample data for onboarding demo mode."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from core.db.repositories.categories import get_all_categories
from core.db.repositories.mei import create_mei_client, create_mei_invoice
from core.db.repositories.mei_inventory import create_product
from core.db.repositories.mei_orders import create_order
from core.db.repositories.mei_recurring import create_subscription
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import create_transaction
from core.mei_operational import enabled_modules
from core.models import (
    MeiClient,
    MeiInvoice,
    MeiOrder,
    MeiProduct,
    MeiSubscription,
    Transaction,
    TransactionType,
)
from core.services.mei_service import create_mei_profile

_DEMO_NOTE = "demo:onboarding"


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
                    notes=_DEMO_NOTE,
                )
            )
            created += 1
        except Exception:
            continue
    return created


def seed_demo_mei_data(
    *,
    operational_profile: str = "on_demand",
    cnae: str | None = None,
    settings: Mapping[str, Any] | None = None,
) -> tuple[int, int | None]:
    """Create demo MEI profile and sample business records. Returns (count, profile_id)."""
    profile, _ = create_mei_profile(
        name="MEI Demo",
        razao_social="Maria Silva Serviços ME",
        cnpj="12.345.678/0001-90",
        activity_type="servico",
        operational_profile=operational_profile,
        cnae=cnae,
    )
    profile_id = profile.id
    if settings is not None and hasattr(settings, "__setitem__"):
        settings["mei_profile_id"] = profile_id
        if settings.get("setup_mode") == "mei":
            settings["selected_profile_id"] = profile_id

    categories = {c.name: c for c in get_all_categories()}
    revenue = categories.get("Receita MEI")
    materials = categories.get("Materiais e Insumos")
    marketing = categories.get("Marketing MEI")
    if not revenue:
        return 0, profile_id

    today = date.today()
    day = min(today.day, 28)
    created = 0

    client = create_mei_client(
        MeiClient(profile_id=profile_id, name="Cliente Demo Ltda", document="11.222.333/0001-81")
    )
    created += 1

    for desc, amount, cat_id, tx_type, tx_day in (
        ("Projeto demo", Decimal("2800"), revenue.id, TransactionType.INCOME, 5),
        ("Serviço avulso demo", Decimal("1500"), revenue.id, TransactionType.INCOME, 15),
        ("Insumos demo", Decimal("320"), materials.id if materials else revenue.id, TransactionType.EXPENSE, 8),
        ("Anúncio demo", Decimal("150"), marketing.id if marketing else revenue.id, TransactionType.EXPENSE, 12),
    ):
        if not cat_id:
            continue
        try:
            create_transaction(
                Transaction(
                    profile_id=profile_id,
                    category_id=cat_id,
                    description=desc,
                    amount=amount,
                    date=date(today.year, today.month, min(tx_day, 28)),
                    type=tx_type,
                    notes=_DEMO_NOTE,
                )
            )
            created += 1
        except Exception:
            continue

    try:
        create_mei_invoice(
            MeiInvoice(
                profile_id=profile_id,
                invoice_number="NF-DEMO-001",
                client_id=client.id,
                tomador_name=client.name,
                amount=Decimal("1500"),
                issue_date=date(today.year, today.month, day),
                notes=_DEMO_NOTE,
            )
        )
        created += 1
    except Exception:
        pass

    modules = enabled_modules(operational_profile)
    if "inventory" in modules:
        try:
            create_product(
                MeiProduct(
                    profile_id=profile_id,
                    name="Produto demo",
                    unit_price=Decimal("49.90"),
                    cost_price=Decimal("25"),
                    stock_qty=Decimal("8"),
                    low_stock_threshold=Decimal("3"),
                    notes=_DEMO_NOTE,
                )
            )
            created += 1
        except Exception:
            pass
    if "orders" in modules:
        try:
            create_order(
                MeiOrder(
                    profile_id=profile_id,
                    client_id=client.id,
                    reference="Pedido demo #001",
                    revenue_amount=Decimal("1200"),
                    order_date=date(today.year, today.month, day),
                    notes=_DEMO_NOTE,
                )
            )
            created += 1
        except Exception:
            pass
    if "recurring_billing" in modules:
        try:
            create_subscription(
                MeiSubscription(
                    profile_id=profile_id,
                    client_id=client.id,
                    name="Plano mensal demo",
                    monthly_amount=Decimal("350"),
                    due_day=10,
                    start_date=date(today.year, today.month, 1),
                    notes=_DEMO_NOTE,
                )
            )
            created += 1
        except Exception:
            pass

    return created, profile_id


def seed_demo_onboarding(settings: Mapping[str, Any]) -> tuple[int, int]:
    """Seed demo data according to onboarding setup_mode. Returns (personal, mei) counts."""
    mode = settings.get("setup_mode") or "personal"
    personal = 0
    mei = 0
    if mode in ("personal", "couple", "both"):
        personal = seed_demo_transactions()
    if mode in ("mei", "both"):
        mei, _ = seed_demo_mei_data(
            operational_profile=settings.get("mei_operational_profile") or "on_demand",
            cnae=(settings.get("mei_cnae") or "").strip() or None,
            settings=settings,
        )
    return personal, mei