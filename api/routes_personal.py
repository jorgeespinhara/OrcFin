"""FastAPI router for Phase 2 personal modules: Cards, Import, Investments, Reports/AI, Settings."""

from __future__ import annotations

import base64
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.ai_gateway import PROVIDERS, get_financial_insights
from core.backup import create_backup, list_backups
from core.data_export import export_open_data_json, export_transactions_csv
from core.db.repositories.budgets import (
    delete_budget,
    get_budgets_for_month,
    get_consolidated_budgets_for_month,
    set_budget,
)
from core.db.repositories.categories import create_category, delete_category
from core.db.repositories.credit_cards import (
    create_credit_card,
    delete_credit_card,
    get_card_spending_summary,
    get_credit_cards,
    update_credit_card,
)
from core.db.repositories.goals import (
    create_goal,
    delete_goal,
    get_active_goals,
    update_goal_progress,
)
from core.db.repositories.investment_holdings import create_holding, delete_holding
from core.db.repositories.net_worth import (
    create_asset,
    create_liability,
    delete_asset,
    delete_liability,
    get_assets,
    get_liabilities,
    get_net_worth_totals,
)
from core.db.repositories.profiles import create_profile, delete_profile
from core.db.schema import init_database
from core.diagnostics import export_diagnostics
from core.engine.categorization import create_rule, delete_rule, get_all_rules
from core.engine.local_insights import get_local_finance_insights
from core.engine.recurrence_detection import detect_recurring_transactions
from core.engine.reporting import get_top_expense_categories_with_trend
from core.engine.scenario_simulator import ScenarioAdjustment, simulate_scenario
from core.engine.seasonal_analysis import get_seasonal_expense_comparison
from core.i18n import apply_from_settings
from core.import_parsers.models import ParsedStatementLine, ParseResult
from core.models import (
    Asset,
    CreditCard,
    InvestmentHolding,
    Liability,
    TransactionType,
)
from core.pdf_generator import generate_monthly_report
from core.reset import reset_database
from core.services.import_service import commit_import, prepare_import
from core.services.portfolio_service import get_portfolio_summary, refresh_quotes
from core.settings_store import load_settings, reset_preferences_after_data_wipe, save_settings
from core.update_check import check_for_updates

router = APIRouter(prefix="/api", tags=["personal"])


def _js(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _js(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_js(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return _js(obj.model_dump())
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return _js(vars(obj))
    if hasattr(obj, "value") and not isinstance(obj, (str, bytes)):
        return obj.value
    return obj


# --- Credit Cards ---

class CardPayload(BaseModel):
    profile_id: int
    name: str = Field(min_length=1, max_length=100)
    bank: str = ""
    credit_limit: Decimal = Field(gt=0)
    due_day: int = Field(ge=1, le=31)
    closing_day: int = Field(default=1, ge=1, le=31)


@router.get("/cards")
def list_cards(
    profile_id: int | None = Query(default=None),
    consolidated: bool = Query(default=True),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
) -> dict[str, Any]:
    init_database()
    today = date.today()
    y = year or today.year
    m = month or today.month
    cards = get_credit_cards(None if consolidated else profile_id)
    out = []
    for cd in cards:
        summary = get_card_spending_summary(cd.id, y, m) if cd.id else {}
        spent = float(summary.get("spent", 0) or 0)
        limit_val = float(cd.credit_limit or 0)
        pct = (spent / limit_val * 100.0) if limit_val > 0 else 0.0
        out.append(
            {
                "id": cd.id,
                "profile_id": cd.profile_id,
                "name": cd.name,
                "credit_limit": limit_val,
                "due_day": cd.due_day,
                "closing_day": getattr(cd, "closing_day", 1),
                "spent": spent,
                "available": max(0.0, limit_val - spent),
                "usage_pct": round(pct, 1),
                "tx_count": int(summary.get("count", 0) or 0),
            }
        )
    return _js({"items": out, "year": y, "month": m})


@router.post("/cards")
def create_card_ep(payload: CardPayload) -> dict[str, Any]:
    init_database()
    card = create_credit_card(
        CreditCard(
            profile_id=payload.profile_id,
            name=payload.name.strip(),
            bank=payload.bank.strip() or payload.name.strip(),
            credit_limit=payload.credit_limit,
            due_day=payload.due_day,
            closing_day=payload.closing_day,
        )
    )
    return _js({"id": card.id})


@router.put("/cards/{card_id}")
def update_card_ep(card_id: int, payload: CardPayload) -> dict[str, Any]:
    ok = update_credit_card(
        CreditCard(
            id=card_id,
            profile_id=payload.profile_id,
            name=payload.name.strip(),
            bank=payload.bank.strip() or payload.name.strip(),
            credit_limit=payload.credit_limit,
            due_day=payload.due_day,
            closing_day=payload.closing_day,
        )
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"updated": True}


@router.delete("/cards/{card_id}")
def delete_card_ep(card_id: int) -> dict[str, Any]:
    ok = delete_credit_card(card_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"deleted": True}


# --- Import (OFX / CSV / PDF) ---

class ImportPreviewPayload(BaseModel):
    filename: str
    content_b64: str
    profile_id: int


class ImportCommitLine(BaseModel):
    date: date
    description: str
    amount: Decimal = Field(gt=0)
    type: Literal["income", "expense"]
    category_id: int
    selected: bool = True


class ImportCommitPayload(BaseModel):
    profile_id: int
    filename: str = "import"
    source: str = "manual"
    credit_card_id: int | None = None
    lines: list[ImportCommitLine]


@router.post("/import/preview")
def import_preview_ep(payload: ImportPreviewPayload) -> dict[str, Any]:
    init_database()
    try:
        raw = base64.b64decode(payload.content_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 file content")
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 15 MB limit")

    res = prepare_import(raw, payload.filename, payload.profile_id)
    lines = []
    for idx, line in enumerate(res.lines):
        lines.append(
            {
                "index": idx,
                "date": line.date.isoformat(),
                "description": line.description,
                "amount": float(line.amount),
                "type": line.type.value,
                "suggested_category_id": line.suggested_category_id,
                "is_duplicate": bool(line.is_duplicate),
                "confidence": float(getattr(line, "confidence", 0.0) or 0.0),
            }
        )
    return _js(
        {
            "source": res.source,
            "institution": getattr(res, "institution", ""),
            "warnings": list(res.warnings or []),
            "lines": lines,
            "total": len(lines),
            "duplicates": sum(1 for l in lines if l["is_duplicate"]),
        }
    )


@router.post("/import/commit")
def import_commit_ep(payload: ImportCommitPayload) -> dict[str, Any]:
    init_database()
    chosen = [
        ParsedStatementLine(
            date=item.date,
            description=item.description.strip(),
            amount=item.amount,
            type=TransactionType(item.type),
            suggested_category_id=item.category_id,
            is_duplicate=False,
        )
        for item in payload.lines
        if item.selected
    ]
    if not chosen:
        return {"imported": 0, "batch_id": None}
    pr = ParseResult(source=payload.source, lines=chosen)
    count, batch_id = commit_import(
        pr,
        payload.profile_id,
        lines=chosen,
        credit_card_id=payload.credit_card_id,
    )
    return {"imported": count, "batch_id": batch_id}


# --- Investments ---

class HoldingPayload(BaseModel):
    profile_id: int
    name: str = Field(min_length=1, max_length=120)
    ticker: str = ""
    asset_class: str = "acoes"
    quantity: Decimal = Field(gt=0)
    avg_price: Decimal = Field(ge=0)
    institution: str = ""


@router.get("/investments")
def investments_summary_ep(profile_id: int = Query(...)) -> dict[str, Any]:
    init_database()
    settings = load_settings()
    summary = get_portfolio_summary(profile_id, settings=settings)
    return _js(summary)


@router.post("/investments")
def create_holding_ep(payload: HoldingPayload) -> dict[str, Any]:
    init_database()
    h = create_holding(
        InvestmentHolding(
            profile_id=payload.profile_id,
            name=payload.name.strip(),
            ticker=payload.ticker.strip().upper() or None,
            asset_class=payload.asset_class,
            quantity=payload.quantity,
            avg_price=payload.avg_price,
            institution=payload.institution.strip() or None,
        )
    )
    return _js({"id": h.id})


@router.delete("/investments/{holding_id}")
def delete_holding_ep(holding_id: int) -> dict[str, Any]:
    ok = delete_holding(holding_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"deleted": True}


@router.post("/investments/refresh-quotes")
def refresh_quotes_ep(profile_id: int = Query(...)) -> dict[str, Any]:
    init_database()
    settings = load_settings()
    res = refresh_quotes(profile_id, settings=settings)
    return _js(res)


# --- Reports & AI ---

class SimulatePayload(BaseModel):
    profile_id: int | None = None
    consolidated: bool = True
    months_ahead: int = Field(default=12, ge=1, le=36)
    kind: Literal["expense_pct", "income_pct", "monthly_cut", "extra_income"] = "expense_pct"
    value: float = 10.0


class PdfPayload(BaseModel):
    profile_id: int | None = None
    consolidated: bool = True
    year: int
    month: int


class AiPayload(BaseModel):
    profile_id: int | None = None
    consolidated: bool = True
    provider: str | None = None


@router.get("/reports")
def reports_overview_ep(
    profile_id: int | None = Query(default=None),
    consolidated: bool = Query(default=True),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
) -> dict[str, Any]:
    init_database()
    today = date.today()
    y = year or today.year
    m = month or today.month
    eff_pid = None if consolidated else profile_id

    seasonal = get_seasonal_expense_comparison(
        profile_id=eff_pid, consolidated=consolidated, reference_year=y
    )
    trends = get_top_expense_categories_with_trend(
        profile_id=eff_pid, consolidated=consolidated, end_year=y, end_month=m, limit=5
    )
    recurrences = detect_recurring_transactions(
        profile_id=eff_pid, consolidated=consolidated
    )[:8]
    insights = get_local_finance_insights(
        profile_id=eff_pid, consolidated=consolidated, year=y, month=m, limit=5
    )
    settings = load_settings()
    return _js(
        {
            "seasonal": seasonal,
            "top_trends": trends,
            "recurrences": recurrences,
            "local_insights": insights,
            "ai_provider": settings.get("ai_provider", "deepseek"),
            "providers": [
                {"id": k, "name": v.get("name", k)} for k, v in PROVIDERS.items()
            ],
        }
    )


@router.post("/reports/simulate")
def reports_simulate_ep(payload: SimulatePayload) -> dict[str, Any]:
    init_database()
    eff_pid = None if payload.consolidated else payload.profile_id
    adj_map = {
        "expense_pct": ScenarioAdjustment(kind="expense_pct", value=-abs(payload.value)),
        "income_pct": ScenarioAdjustment(kind="income_pct", value=abs(payload.value)),
        "monthly_cut": ScenarioAdjustment(kind="expense_delta", value=-abs(payload.value)),
        "extra_income": ScenarioAdjustment(kind="income_delta", value=abs(payload.value)),
    }
    res = simulate_scenario(
        profile_id=eff_pid,
        consolidated=payload.consolidated,
        months_ahead=payload.months_ahead,
        adjustments=[adj_map[payload.kind]],
    )
    return _js(res)


@router.post("/reports/pdf")
def reports_pdf_ep(payload: PdfPayload) -> dict[str, Any]:
    init_database()
    eff_pid = None if payload.consolidated else payload.profile_id
    path = generate_monthly_report(
        year=payload.year,
        month=payload.month,
        consolidated=payload.consolidated,
        profile_id=eff_pid,
    )
    return {"path": str(path)}


@router.post("/reports/ai")
def reports_ai_ep(payload: AiPayload) -> dict[str, Any]:
    init_database()
    settings = load_settings()
    provider = payload.provider or settings.get("ai_provider", "deepseek")
    api_key = settings.get("ai_api_key") or None
    eff_pid = None if payload.consolidated else payload.profile_id
    res = get_financial_insights(
        provider=provider,
        api_key=api_key,
        settings=settings,
        profile_id=eff_pid,
        consolidated=payload.consolidated,
        model=settings.get("ai_model") or None,
        base_url=settings.get("ai_base_url") or None,
        use_fallback_on_error=True,
    )
    return _js(res)


# --- Settings, Goals, Budgets, Rules, Net Worth, Backup, Export, Diagnostics, Updates ---

class ProfilePayload(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = "#14B8A6"


class CategoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: Literal["income", "expense"]
    icon: str = ""


class GoalPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: float = Field(gt=0)
    profile_id: int | None = None


class GoalProgressPayload(BaseModel):
    add_amount: float


class BudgetPayload(BaseModel):
    profile_id: int | None = None
    category_id: int
    year: int
    month: int
    limit_amount: float = Field(gt=0)


class RulePayload(BaseModel):
    pattern: str = Field(min_length=1, max_length=100)
    category_id: int
    match_type: Literal["contains", "starts_with", "exact"] = "contains"


class AssetPayload(BaseModel):
    profile_id: int
    name: str = Field(min_length=1, max_length=100)
    value: Decimal = Field(ge=0)
    asset_type: str = "other"


class LiabilityPayload(BaseModel):
    profile_id: int
    name: str = Field(min_length=1, max_length=100)
    balance: Decimal = Field(ge=0)
    liability_type: str = "other"


class SettingsUpdatePayload(BaseModel):
    locale: str | None = None
    country_profile: str | None = None
    currency: str | None = None
    theme_mode: Literal["dark", "light"] | None = None
    strict_offline: bool | None = None
    backup_on_close: bool | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_base_url: str | None = None
    ai_api_key: str | None = None


@router.post("/profiles")
def create_profile_ep(payload: ProfilePayload) -> dict[str, Any]:
    p = create_profile(payload.name.strip(), payload.color)
    return _js({"id": p.id})


@router.delete("/profiles/{profile_id}")
def delete_profile_ep(profile_id: int) -> dict[str, Any]:
    ok = delete_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}


@router.post("/categories")
def create_category_ep(payload: CategoryPayload) -> dict[str, Any]:
    c = create_category(payload.name.strip(), TransactionType(payload.type), payload.icon or None)
    return _js({"id": c.id})


@router.delete("/categories/{cat_id}")
def delete_category_ep(cat_id: int) -> dict[str, Any]:
    ok = delete_category(cat_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"deleted": True}


@router.get("/goals")
def list_goals_ep(profile_id: int | None = Query(default=None)) -> dict[str, Any]:
    init_database()
    return _js({"items": get_active_goals(profile_id)})


@router.post("/goals")
def create_goal_ep(payload: GoalPayload) -> dict[str, Any]:
    gid = create_goal(payload.name.strip(), payload.target_amount, None, payload.profile_id)
    return {"id": gid}


@router.post("/goals/{goal_id}/progress")
def progress_goal_ep(goal_id: int, payload: GoalProgressPayload) -> dict[str, Any]:
    ok = update_goal_progress(goal_id, payload.add_amount)
    if not ok:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"updated": True}


@router.delete("/goals/{goal_id}")
def delete_goal_ep(goal_id: int) -> dict[str, Any]:
    ok = delete_goal(goal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"deleted": True}


@router.get("/budgets")
def list_budgets_ep(
    year: int = Query(...),
    month: int = Query(...),
    profile_id: int | None = Query(default=None),
    consolidated: bool = Query(default=True),
) -> dict[str, Any]:
    init_database()
    items = (
        get_consolidated_budgets_for_month(year, month)
        if consolidated
        else get_budgets_for_month(year, month, profile_id)
    )
    return _js({"items": items})


@router.post("/budgets")
def set_budget_ep(payload: BudgetPayload) -> dict[str, Any]:
    set_budget(
        payload.profile_id,
        payload.category_id,
        payload.year,
        payload.month,
        payload.limit_amount,
    )
    return {"saved": True}


@router.delete("/budgets/{budget_id}")
def delete_budget_ep(budget_id: int) -> dict[str, Any]:
    delete_budget(budget_id)
    return {"deleted": True}


@router.get("/rules")
def list_rules_ep() -> dict[str, Any]:
    init_database()
    return _js({"items": get_all_rules()})


@router.post("/rules")
def create_rule_ep(payload: RulePayload) -> dict[str, Any]:
    rid = create_rule(payload.pattern.strip(), payload.category_id, payload.match_type)
    return {"id": rid}


@router.delete("/rules/{rule_id}")
def delete_rule_ep(rule_id: int) -> dict[str, Any]:
    delete_rule(rule_id)
    return {"deleted": True}


@router.get("/net-worth")
def net_worth_ep(profile_id: int = Query(...)) -> dict[str, Any]:
    init_database()
    return _js(
        {
            "totals": get_net_worth_totals(profile_id),
            "assets": get_assets(profile_id),
            "liabilities": get_liabilities(profile_id),
        }
    )


@router.post("/assets")
def create_asset_ep(payload: AssetPayload) -> dict[str, Any]:
    a = create_asset(
        Asset(
            profile_id=payload.profile_id,
            name=payload.name.strip(),
            value=payload.value,
            asset_type=payload.asset_type,
        )
    )
    return _js({"id": a.id})


@router.delete("/assets/{asset_id}")
def delete_asset_ep(asset_id: int) -> dict[str, Any]:
    delete_asset(asset_id)
    return {"deleted": True}


@router.post("/liabilities")
def create_liability_ep(payload: LiabilityPayload) -> dict[str, Any]:
    li = create_liability(
        Liability(
            profile_id=payload.profile_id,
            name=payload.name.strip(),
            balance=payload.balance,
            liability_type=payload.liability_type,
        )
    )
    return _js({"id": li.id})


@router.delete("/liabilities/{liability_id}")
def delete_liability_ep(liability_id: int) -> dict[str, Any]:
    delete_liability(liability_id)
    return {"deleted": True}


@router.get("/settings")
def get_settings_ep() -> dict[str, Any]:
    s = load_settings()
    provider = s.get("ai_provider", "deepseek")
    has_key = bool(s.get("ai_api_key"))
    backups = [str(p.name) for p in list_backups()[:10]]
    return _js(
        {
            "locale": s.get("locale", "pt-BR"),
            "country_profile": s.get("country_profile", "BR"),
            "currency": s.get("currency", "BRL"),
            "theme_mode": s.get("theme_mode", "dark"),
            "strict_offline": bool(s.get("strict_offline", False)),
            "backup_on_close": bool(s.get("backup_on_close", False)),
            "ai_provider": provider,
            "ai_model": s.get("ai_model", ""),
            "ai_base_url": s.get("ai_base_url", ""),
            "ai_has_key": has_key,
            "backups": backups,
            "providers": [
                {"id": k, "name": v.get("name", k)} for k, v in PROVIDERS.items()
            ],
        }
    )


@router.put("/settings")
def update_settings_ep(payload: SettingsUpdatePayload) -> dict[str, Any]:
    s = load_settings()
    for field in (
        "locale",
        "country_profile",
        "currency",
        "theme_mode",
        "strict_offline",
        "backup_on_close",
        "ai_provider",
        "ai_model",
        "ai_base_url",
    ):
        val = getattr(payload, field)
        if val is not None:
            s[field] = val
    if payload.ai_api_key and payload.ai_api_key.strip():
        s["ai_api_key"] = payload.ai_api_key.strip()
    apply_from_settings(s)
    save_settings(s)
    return {"saved": True}


@router.post("/backup/create")
def backup_create_ep() -> dict[str, Any]:
    path = create_backup()
    return {"path": str(path)}


@router.post("/export/csv")
def export_csv_ep(profile_id: int | None = Query(default=None)) -> dict[str, Any]:
    path = export_transactions_csv(profile_id)
    return {"path": str(path)}


@router.post("/export/json")
def export_json_ep(profile_id: int | None = Query(default=None)) -> dict[str, Any]:
    path = export_open_data_json(profile_id)
    return {"path": str(path)}


@router.post("/diagnostics/export")
def diagnostics_export_ep() -> dict[str, Any]:
    path = export_diagnostics()
    return {"path": str(path)}


@router.get("/updates/check")
def updates_check_ep() -> dict[str, Any]:
    return check_for_updates()


@router.post("/reset/financial")
def reset_financial_ep() -> dict[str, Any]:
    reset_database()
    reset_preferences_after_data_wipe()
    return {"reset": True}
