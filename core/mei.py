"""MEI module — revenue limit, NF tracking, simplified P&L."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.db.queries import get_monthly_summary, get_ytd_totals
from core.db.repositories.mei import get_mei_clients, get_mei_config, get_mei_invoices
from core.db.repositories.transactions import get_transactions
from core.domain.entities.mei_profile import MEI_ANNUAL_LIMIT_DEFAULT, MeiProfile
from core.models import MeiConfig, TransactionType
from core.services.mei_service import das_payment_exists


def get_ytd_revenue(profile_id: int, year: Optional[int] = None) -> Decimal:
    year = year or date.today().year
    totals = get_ytd_totals(year, date.today().month, profile_id=profile_id)
    return totals["total_income"]


def _mei_entity(profile_id: int, annual_limit: Optional[Decimal] = None) -> Optional[MeiProfile]:
    config = get_mei_config(profile_id)
    if config is None:
        return None
    if annual_limit is not None:
        config = config.model_copy(update={"annual_limit": float(annual_limit)})
    return MeiProfile(config)


def get_revenue_limit_status(
    profile_id: int,
    annual_limit: Optional[Decimal] = None,
) -> Dict[str, Any]:
    entity = _mei_entity(profile_id, annual_limit)
    if entity is None:
        limit = annual_limit or MEI_ANNUAL_LIMIT_DEFAULT
        entity = MeiProfile(
            MeiConfig(
                profile_id=profile_id,
                razao_social="",
                cnpj="",
                annual_limit=float(limit),
            )
        )
    return entity.revenue_limit_status(get_ytd_revenue(profile_id))


def get_simplified_report(
    profile_id: int,
    year: Optional[int] = None,
    deductible_category_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Receita bruta, despesas dedutíveis/não dedutíveis, resultado simplificado."""
    year = year or date.today().year
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    txs = get_transactions(profile_id=profile_id, start_date=start, end_date=end, limit=5000)

    deductible_ids = set(deductible_category_ids or [])
    gross_revenue = Decimal("0")
    deductible_expenses = Decimal("0")
    non_deductible_expenses = Decimal("0")

    for tx in txs:
        if tx.type == TransactionType.INCOME:
            gross_revenue += tx.amount
        else:
            if deductible_ids and tx.category_id in deductible_ids:
                deductible_expenses += tx.amount
            else:
                non_deductible_expenses += tx.amount

    result = gross_revenue - deductible_expenses
    return {
        "year": year,
        "gross_revenue": gross_revenue,
        "deductible_expenses": deductible_expenses,
        "non_deductible_expenses": non_deductible_expenses,
        "simplified_result": result,
        "transaction_count": len(txs),
    }


def get_invoice_reconciliation(profile_id: int, year: Optional[int] = None) -> Dict[str, Any]:
    """Compare NF totals vs recorded income."""
    year = year or date.today().year
    invoices = get_mei_invoices(profile_id, year=year)
    nf_total = sum(Decimal(str(inv["amount"])) for inv in invoices)
    ytd_income = get_ytd_revenue(profile_id, year)
    diff = ytd_income - nf_total
    return {
        "invoice_total": nf_total,
        "recorded_income": ytd_income,
        "difference": diff,
        "invoice_count": len(invoices),
        "aligned": abs(diff) < Decimal("0.01"),
    }


def get_revenue_by_client(profile_id: int, year: Optional[int] = None) -> List[Dict[str, Any]]:
    """Aggregate income transactions by client/tomador."""
    year = year or date.today().year
    clients = {c.id: c.name for c in get_mei_clients(profile_id)}
    txs = get_transactions(
        profile_id=profile_id,
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
        limit=5000,
    )
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    for tx in txs:
        if tx.type != TransactionType.INCOME:
            continue
        if tx.mei_client_id and tx.mei_client_id in clients:
            name = clients[tx.mei_client_id]
        else:
            name = "Sem cliente vinculado"
        totals[name] += tx.amount
        counts[name] += 1

    return sorted(
        [
            {"name": name, "total": total, "count": counts[name]}
            for name, total in totals.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )


def get_ytd_revenue_evolution(profile_id: int, year: Optional[int] = None) -> List[Dict[str, Any]]:
    """Cumulative YTD revenue by month (for limit chart)."""
    year = year or date.today().year
    today = date.today()
    cumulative = Decimal("0")
    points = []
    for month in range(1, today.month + 1):
        summary = get_monthly_summary(year, month, profile_id)
        cumulative += summary["total_income"]
        points.append({
            "month": month,
            "label": f"{month:02d}/{year}",
            "monthly_income": summary["total_income"],
            "cumulative": cumulative,
        })
    return points


def get_obligations_checklist(profile_id: int) -> List[Dict[str, Any]]:
    """Monthly MEI obligation checklist (offline, no gov integration)."""
    today = date.today()
    config = get_mei_config(profile_id)
    entity = MeiProfile(config) if config else None
    das_info = entity.das_due_info(today) if entity else {"is_urgent": False}

    recon = get_invoice_reconciliation(profile_id, today.year)
    limit = get_revenue_limit_status(profile_id)
    das_ok = das_payment_exists(profile_id, today.year, today.month)
    invoices = get_mei_invoices(profile_id, year=today.year)
    nf_this_month = any(
        str(inv.get("issue_date", "")).startswith(f"{today.year}-{today.month:02d}")
        for inv in invoices
    )
    month_name = [
        "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez",
    ][today.month]

    return [
        {
            "id": "das",
            "label": f"DAS de {month_name}/{today.year} confirmado no app",
            "done": das_ok,
            "urgent": not das_ok and das_info.get("is_urgent", False),
            "hint": "Pague no Simples Nacional e confirme aqui",
        },
        {
            "id": "nf_month",
            "label": f"Notas fiscais de {month_name} registradas",
            "done": nf_this_month,
            "urgent": False,
            "hint": "Registre cada NF emitida para conferência",
        },
        {
            "id": "reconcile",
            "label": "Faturamento lançado vs notas fiscais",
            "done": recon["aligned"],
            "urgent": not recon["aligned"] and recon["invoice_count"] > 0,
            "hint": f"Diferença: R$ {abs(recon['difference']):.2f}" if not recon["aligned"] else "Conferido",
        },
        {
            "id": "limit",
            "label": "Dentro do limite de faturamento anual",
            "done": not limit.get("exceeded", False),
            "urgent": limit.get("at_risk", False),
            "hint": f"{limit.get('percentage', 0):.0f}% do limite usado",
        },
    ]


def get_mei_dashboard_data(profile_id: int) -> Dict[str, Any]:
    """KPIs for MEI home dashboard."""
    today = date.today()
    monthly = get_monthly_summary(today.year, today.month, profile_id)
    ytd = get_ytd_totals(today.year, today.month, profile_id=profile_id)
    limit = get_revenue_limit_status(profile_id)
    by_client = get_revenue_by_client(profile_id, today.year)
    evolution = get_ytd_revenue_evolution(profile_id, today.year)

    month_income = monthly["total_income"]
    month_expense = monthly["total_expense"]
    client_count = len(by_client)
    ticket = (month_income / client_count) if client_count > 0 else Decimal("0")

    return {
        "month_income": month_income,
        "month_expense": month_expense,
        "ytd_income": ytd["total_income"],
        "ytd_expense": ytd["total_expense"],
        "limit_status": limit,
        "revenue_by_client": by_client,
        "ytd_evolution": evolution,
        "ticket_medio": ticket.quantize(Decimal("0.01")),
        "client_count": client_count,
    }