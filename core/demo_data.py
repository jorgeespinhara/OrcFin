"""Sample data for onboarding demo mode."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from core.db.repositories.budgets import set_budget
from core.db.repositories.categories import get_all_categories
from core.db.repositories.goals import create_goal, update_goal_progress
from core.db.repositories.mei import create_mei_client, create_mei_invoice
from core.db.repositories.mei_inventory import create_product
from core.db.repositories.mei_orders import create_order
from core.db.repositories.mei_recurring import create_subscription
from core.db.repositories.net_worth import create_asset, create_liability
from core.db.repositories.profiles import get_all_profiles
from core.db.repositories.transactions import create_transaction
from core.domain.entities.mei_profile import MeiProfile
from core.domain.enums import ProfileType
from core.mei_operational import enabled_modules
from core.models import (
    Asset,
    Liability,
    MeiClient,
    MeiInvoice,
    MeiOrder,
    MeiProduct,
    MeiSubscription,
    Transaction,
    TransactionType,
)
from core.services.mei_service import confirm_das_payment, create_mei_profile

_DEMO_NOTE = "demo:onboarding"
_HISTORY_MONTHS = 12


def _safe_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, 28))


def _iter_months(count: int, *, end: date | None = None) -> list[tuple[int, int]]:
    end = end or date.today()
    year, month = end.year, end.month
    months: list[tuple[int, int]] = []
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()
    return months


def _cat_map() -> dict[str, int]:
    return {c.name: c.id for c in get_all_categories()}


def _add_tx(
    profile_id: int,
    *,
    description: str,
    amount: Decimal,
    category_id: int,
    tx_type: TransactionType,
    tx_date: date,
) -> bool:
    try:
        create_transaction(
            Transaction(
                profile_id=profile_id,
                category_id=category_id,
                description=description,
                amount=amount,
                date=tx_date,
                type=tx_type,
                notes=_DEMO_NOTE,
            )
        )
        return True
    except Exception:
        return False


def _personal_month_plan(
    profile_idx: int,
    month_idx: int,
    year: int,
    month: int,
    cats: dict[str, int],
) -> list[tuple[str, Decimal, str, TransactionType, int]]:
    """Return demo transactions for one personal profile/month."""
    salary = Decimal("4800") if profile_idx == 0 else Decimal("3900")
    rent = Decimal("1350") if profile_idx == 0 else Decimal("980")
    seasonal = Decimal("1") + Decimal(str(month_idx % 3)) * Decimal("0.08")
    txs: list[tuple[str, Decimal, str, TransactionType, int]] = [
        ("Salário demo", salary, "Salário", TransactionType.INCOME, 1),
        ("Moradia demo", rent, "Moradia (Aluguel/Financiamento/Condomínio)", TransactionType.EXPENSE, 5),
        ("Supermercado demo", Decimal("420") * seasonal, "Alimentação (Mercado + Refeições)", TransactionType.EXPENSE, 7),
        ("Restaurante demo", Decimal("145"), "Alimentação (Mercado + Refeições)", TransactionType.EXPENSE, 14),
        ("Combustível demo", Decimal("210"), "Transporte (Combustível/Uber/Transporte Público)", TransactionType.EXPENSE, 9),
        ("Contas demo", Decimal("285"), "Utilities (Luz, Água, Gás, Internet)", TransactionType.EXPENSE, 10),
        ("Streaming demo", Decimal("89.90"), "Assinaturas (Streaming, Apps, etc.)", TransactionType.EXPENSE, 12),
    ]
    if month_idx % 2 == 0:
        txs.append(
            ("Freelance demo", Decimal("750") + month_idx * Decimal("40"), "Renda Extra / Freelance", TransactionType.INCOME, 18)
        )
    if month_idx % 3 == 0:
        txs.append(
            ("Dividendos demo", Decimal("320"), "Investimentos (Dividendos/Juros)", TransactionType.INCOME, 22)
        )
    if month_idx % 4 == 1:
        txs.append(("Farmácia demo", Decimal("95"), "Saúde (Plano + Medicamentos + Consultas)", TransactionType.EXPENSE, 16))
    if month_idx % 5 == 2:
        txs.append(("Curso demo", Decimal("180"), "Educação (Escola/Cursos)", TransactionType.EXPENSE, 20))
    if month in (6, 7, 12):
        txs.append(("Lazer demo", Decimal("240"), "Lazer e Entretenimento", TransactionType.EXPENSE, 21))
    if month == 12:
        txs.append(("Presentes demo", Decimal("310"), "Presentes e Doações", TransactionType.EXPENSE, 23))
    if month in (1, 7):
        txs.append(("Viagem demo", Decimal("680"), "Viagens e Férias", TransactionType.EXPENSE, 26))
    if profile_idx == 1:
        txs.append(("Academia demo", Decimal("129"), "Roupas e Cuidados Pessoais", TransactionType.EXPENSE, 11))
    return txs


def _seed_personal_profile(profile_id: int, profile_idx: int, cats: dict[str, int]) -> int:
    created = 0
    for month_idx, (year, month) in enumerate(_iter_months(_HISTORY_MONTHS)):
        for desc, amount, cat_name, tx_type, day in _personal_month_plan(
            profile_idx, month_idx, year, month, cats
        ):
            cat_id = cats.get(cat_name)
            if not cat_id:
                continue
            if _add_tx(
                profile_id,
                description=desc,
                amount=amount.quantize(Decimal("0.01")),
                category_id=cat_id,
                tx_type=tx_type,
                tx_date=_safe_date(year, month, day),
            ):
                created += 1
    return created


def _seed_personal_extras(profile_id: int, cats: dict[str, int]) -> int:
    created = 0
    today = date.today()
    try:
        goal_id = create_goal(
            "Reserva de emergência demo",
            15000.0,
            date(today.year, 12, 31),
            profile_id,
        )
        if update_goal_progress(goal_id, 6200.0):
            created += 1
        goal_id = create_goal("Viagem demo", 5000.0, date(today.year + 1, 6, 30), profile_id)
        if update_goal_progress(goal_id, 1800.0):
            created += 1
    except Exception:
        pass

    for cat_name, limit in (
        ("Alimentação (Mercado + Refeições)", 900.0),
        ("Transporte (Combustível/Uber/Transporte Público)", 450.0),
        ("Lazer e Entretenimento", 350.0),
    ):
        cat_id = cats.get(cat_name)
        if not cat_id:
            continue
        try:
            if set_budget(profile_id, cat_id, today.year, today.month, limit):
                created += 1
        except Exception:
            continue

    extras = [
        Asset(profile_id=profile_id, name="Conta corrente demo", asset_type="cash", current_value=Decimal("8500"), notes=_DEMO_NOTE),
        Asset(profile_id=profile_id, name="CDB demo", asset_type="investment", current_value=Decimal("12000"), notes=_DEMO_NOTE),
        Asset(profile_id=profile_id, name="Veículo demo", asset_type="vehicle", current_value=Decimal("45000"), notes=_DEMO_NOTE),
        Liability(profile_id=profile_id, name="Cartão parcelado demo", liability_type="credit_card", current_balance=Decimal("2400"), notes=_DEMO_NOTE),
    ]
    for item in extras:
        try:
            if isinstance(item, Asset):
                create_asset(item)
            else:
                create_liability(item)
            created += 1
        except Exception:
            continue
    return created


def seed_demo_transactions(*, couple: bool = False) -> int:
    profiles = [p for p in get_all_profiles() if p.profile_type == ProfileType.PERSONAL]
    if not profiles:
        return 0
    cats = _cat_map()
    if not cats.get("Salário") or not cats.get("Alimentação (Mercado + Refeições)"):
        return 0

    targets = profiles[:2] if couple else profiles[:1]
    created = 0
    for idx, profile in enumerate(targets):
        if profile.id is None:
            continue
        created += _seed_personal_profile(profile.id, idx, cats)
        created += _seed_personal_extras(profile.id, cats)
    return created


def _mei_month_plan(
    month_idx: int,
    year: int,
    month: int,
    cats: dict[str, int],
) -> list[tuple[str, Decimal, str, TransactionType, int]]:
    base_rev = Decimal("3200") + Decimal(str(month_idx * 180))
    txs: list[tuple[str, Decimal, str, TransactionType, int]] = [
        ("Projeto demo", base_rev, "Receita MEI", TransactionType.INCOME, 4),
        ("Serviço avulso demo", Decimal("1200") + month_idx * Decimal("50"), "Receita MEI", TransactionType.INCOME, 16),
        ("Insumos demo", Decimal("280") + month_idx * Decimal("15"), "Materiais e Insumos", TransactionType.EXPENSE, 8),
        ("Marketing demo", Decimal("160"), "Marketing MEI", TransactionType.EXPENSE, 11),
        ("Administrativo demo", Decimal("95"), "Despesas Administrativas MEI", TransactionType.EXPENSE, 13),
    ]
    if month_idx % 4 == 0:
        txs.append(("Equipamento demo", Decimal("890"), "Equipamentos MEI", TransactionType.EXPENSE, 19))
    if month_idx % 2 == 1:
        txs.append(("Consultoria demo", Decimal("2100"), "Receita MEI", TransactionType.INCOME, 24))
    return txs


def seed_demo_mei_data(
    *,
    operational_profile: str = "on_demand",
    cnae: str | None = None,
    settings: Mapping[str, Any] | None = None,
) -> tuple[int, int | None]:
    """Create demo MEI profile and sample business records. Returns (count, profile_id)."""
    profile, config = create_mei_profile(
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

    cats = _cat_map()
    revenue_id = cats.get("Receita MEI")
    if not revenue_id:
        return 0, profile_id

    today = date.today()
    created = 0
    entity = MeiProfile(config)
    das_amount = entity.das_amount()

    clients_data = [
        ("Cliente Demo Ltda", "11.222.333/0001-81"),
        ("Tech Solutions SA", "22.333.444/0001-72"),
        ("Maria Oliveira", "123.456.789-00"),
        ("Construtora Horizonte", "33.444.555/0001-63"),
    ]
    clients: list[MeiClient] = []
    for name, document in clients_data:
        try:
            clients.append(
                create_mei_client(MeiClient(profile_id=profile_id, name=name, document=document, notes=_DEMO_NOTE))
            )
            created += 1
        except Exception:
            continue
    if not clients:
        return created, profile_id

    for month_idx, (year, month) in enumerate(_iter_months(_HISTORY_MONTHS)):
        for desc, amount, cat_name, tx_type, day in _mei_month_plan(month_idx, year, month, cats):
            cat_id = cats.get(cat_name) or revenue_id
            if _add_tx(
                profile_id,
                description=desc,
                amount=amount.quantize(Decimal("0.01")),
                category_id=cat_id,
                tx_type=tx_type,
                tx_date=_safe_date(year, month, day),
            ):
                created += 1
        if month_idx < _HISTORY_MONTHS - 1 or today.day >= entity.config.das_day:
            try:
                if confirm_das_payment(profile_id, _safe_date(year, month, 20), das_amount):
                    created += 1
            except Exception:
                pass

    invoice_months = _iter_months(_HISTORY_MONTHS)
    for month_idx, (year, month) in enumerate(invoice_months):
        client = clients[month_idx % len(clients)]
        inv_count = 2 if month_idx >= len(invoice_months) - 6 else 1
        for seq in range(inv_count):
            amount = Decimal("1500") + Decimal(str((month_idx + seq) * 175))
            try:
                create_mei_invoice(
                    MeiInvoice(
                        profile_id=profile_id,
                        invoice_number=f"NF-DEMO-{year}{month:02d}-{seq + 1:02d}",
                        client_id=client.id,
                        tomador_name=client.name,
                        amount=amount,
                        issue_date=_safe_date(year, month, 5 + seq * 7),
                        due_date=_safe_date(year, month, 15 + seq * 5),
                        notes=_DEMO_NOTE,
                    )
                )
                created += 1
            except Exception:
                continue

    modules = enabled_modules(operational_profile)
    if "inventory" in modules:
        for name, price, cost, stock in (
            ("Produto demo A", "49.90", "25", "12"),
            ("Produto demo B", "89.00", "42", "5"),
            ("Produto demo C", "129.50", "70", "3"),
        ):
            try:
                create_product(
                    MeiProduct(
                        profile_id=profile_id,
                        name=name,
                        unit_price=Decimal(price),
                        cost_price=Decimal(cost),
                        stock_qty=Decimal(stock),
                        low_stock_threshold=Decimal("4"),
                        notes=_DEMO_NOTE,
                    )
                )
                created += 1
            except Exception:
                pass
    if "orders" in modules:
        for idx, (ref, amount, day) in enumerate(
            (
                ("Pedido demo #101", "2200", 6),
                ("Pedido demo #102", "1850", 18),
                ("Pedido demo #103", "3100", 25),
            )
        ):
            try:
                create_order(
                    MeiOrder(
                        profile_id=profile_id,
                        client_id=clients[idx % len(clients)].id,
                        reference=ref,
                        revenue_amount=Decimal(amount),
                        order_date=_safe_date(today.year, today.month, day),
                        notes=_DEMO_NOTE,
                    )
                )
                created += 1
            except Exception:
                pass
    if "recurring_billing" in modules:
        for idx, (name, amount, due_day) in enumerate(
            (
                ("Plano mensal demo", "350", 10),
                ("Suporte recorrente demo", "520", 15),
            )
        ):
            try:
                create_subscription(
                    MeiSubscription(
                        profile_id=profile_id,
                        client_id=clients[idx % len(clients)].id,
                        name=name,
                        monthly_amount=Decimal(amount),
                        due_day=due_day,
                        start_date=date(today.year, max(1, today.month - 5), 1),
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
        personal = seed_demo_transactions(couple=(mode == "couple"))
    if mode in ("mei", "both"):
        mei, _ = seed_demo_mei_data(
            operational_profile=settings.get("mei_operational_profile") or "on_demand",
            cnae=(settings.get("mei_cnae") or "").strip() or None,
            settings=settings,
        )
    return personal, mei